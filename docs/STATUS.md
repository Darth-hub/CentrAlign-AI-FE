# Validation and delivery status

Last checked: October 26, 2026.

| Area | Status | Evidence or next step |
| --- | --- | --- |
| Repository | Published | `Darth-hub/CentrAlign-AI-FE` |
| Backend runtime tests | 49 passing locally | `make test`; temporary SQLite and controlled ERP/model boundaries |
| Python source | Compiles | `python -m compileall -q backend scripts` |
| Compose definition | Validated | `docker compose --env-file .env.example config --quiet` |
| Bootstrap and backup scripts | Shell syntax checked | `bash -n scripts/bootstrap.sh scripts/backup.sh` |
| Frontend | Production build passed locally | TypeScript + Vite; generated dependency lockfile included |
| Identity startup and bootstrap | Verified locally | Keycloak database repair, discovery and realm/client/user configuration succeeded |
| Live ERP workflow | Verified locally | `MAT-MR-2026-00001` → explicit human approval → `PUR-ORD-2026-00001`, USD 370; independent ERP read-back |
| Docker runtime image | Built locally on arm64 | Shared Python 3.13 Bookworm image; API/worker/bootstrap use the same tag |
| OCR runtime dependencies | Container smoke checks passed | Synthetic image and raster PDF recognized through Pillow/PDFium + Tesseract; fixtures present; pip check passed |
| Invoice extraction workflow | Integration pending | Validate representative invoices, model extraction, review and ERP creation |
| Deployment configuration | 6 tests passing locally | Env-file loading, secret rejection, paired configuration and HTTPS/loopback checks |
| Setup check | Passed locally, Docker probe skipped | `make preflight`; no credentials printed |
| Public architecture preview | Implemented | `/architecture` is available without an organization login |
| Public application | Frontend deployed by owner; backend local | Netlify preview is separate from the Docker ERP/identity/worker services; persistent public backend remains unresolved |
| Backup restoration | Drill pending | Restore to a disposable environment and verify records and identity |

## Local backend checks

The suite in `backend/tests_portable/` checks verified tokens, CORS/auth handling, role restrictions, job ownership, duplicate and interrupted jobs, SQL lifecycle persistence, restricted tools, private document paths, model configuration, approved snapshots, fabricated PO completion, invoice review, real subprocess execution, worker startup failure and ERP invoice linkage.

These checks are evidence for those boundaries. They do not establish live ERP/model success or production reliability.

## Hosting

The frontend targets Netlify. The worker, ERPNext, identity and database services require persistent compute and storage. A suitable strictly free, always-online host for the full stack has not been established under the current constraints. See [deployment instructions](NETLIFY_DEPLOYMENT.md).

## Dependency updates

Dependency pull requests require manual review. The inherited auto-merge workflow has been removed after it merged MCP/Tenacity versions outside the model SDK bounds. CI now checks installed package consistency as well as tests. Revisit the documented bounds together with Strands/Gemini SDK upgrades.

## Session recovery

Rejected API sessions now clear the local OIDC user once and return the UI to sign-in, rather than repeatedly reloading the page. The behavior applies to general API, ERP, agent polling and invoice upload requests. Three concurrency/failure regression tests pass alongside the six deployment checks and 18 backend tests. The stable unauthenticated screen was checked in a browser; a fresh successful authenticated workflow remains to be verified.

Backend token rejection logs include only exception categories, never bearer tokens or claim values. This supports diagnosing a persistent rejection after a new sign-in without exposing credentials.

## Keycloak subject claim repair

The existing client omitted Keycloak's default `basic` scope. Live scope evaluation showed the required `sub` claim absent while email and expiry were present; API diagnostics reported `MissingRequiredClaimError`. Bootstrap now explicitly associates every required default scope, including `basic`, for both new and existing clients. Live evaluation after repair confirmed all three required claims are present. The repair preserves existing passwords and keeps signature, issuer, audience, identity and expiry validation intact.

Two bootstrap regression checks cover repairing an existing client and rejecting a missing required scope. OIDC tests also reject otherwise valid tokens missing `sub`, `email` or `exp`. A fresh browser sign-in is needed to obtain a corrected token; a complete live agent workflow remains pending.

Reference: [Keycloak subject mapper and basic scope](https://www.keycloak.org/docs/latest/upgrading/index.html#new-default-client-scope-basic).

## Live tool execution and sourcing

Groq tool responses are validated before release, with a single bounded response retry. Invalid JSON prompt examples and a missing workflow calculator were corrected. Read-only failures now record the failed sourcing stage. Home supplier/order totals use the backend's actual response fields, and rendered source-comment/legacy workflow-title text was removed.

A live Qwen 3.8 arithmetic probe made one verified tool call. A read-only sourcing job (`7ef18f47-5dc5-476c-a4dc-619e2125c8d7`) retrieved real ERP data and returned structured missing-data reasoning rather than a parsing failure: the demo has no purchase-order history, supplier performance data or current safety-equipment agreement that substantiates supplier selection. It did not recommend inventing those facts. Full procurement completion remains pending approved supplier/pricing evidence.

The same run exposed disabled suppliers being returned as active. ERP supplier queries now include/filter the disabled field and map disabled records to inactive, including direct supplier lookups. This boundary is covered by regression tests.

The current default is `qwen/qwen3.8-27b`, selected from this account's live model listing and tested locally. Groq quotas still cause delays; model availability and limits must be checked for each account. See [model/tool reliability](MODEL_TOOL_RELIABILITY.md).

## Synthetic quote inputs

Two explicitly synthetic quotes are persisted in PostgreSQL for `MAT-MR-2026-00001`: SafetyFirst Equipment Co at USD 370 / 7 delivery days, and MRO Warehouse Direct at USD 385 / 10 days. They are not historical orders, real supplier commitments, or historical delivery metrics. The setup command was run twice and preserved the existing quote records on the second run.

The quote tool first checks requisition visibility with the acting user's ERP credentials, then validates current dates, currency, complete quantity/unit coverage and active supplier status. Synthetic quotes force human review after requisition analysis. Regression checks cover identity, ERP visibility, scope, expiry, currency, coverage and inactive suppliers.

The quotation-backed live sourcing check is a separate run; preparing these inputs is not proof of a completed procurement workflow.

## Bounded execution and deterministic quote checks

The previous quote-backed sourcing run reached its 900-second deadline after excessive calculator calls. The portable runtime now uses concise stage-specific prompts, Qwen instruct mode, a shared tool-call budget and Strands invocation-turn limits. Exhaustion is a failure, never a fabricated completed result. Interrupted workflow processes retain their durable lock and mark the lifecycle failed pending reconciliation.

The next full run completed sourcing and requisition analysis in approximately five minutes and stopped at `PENDING_APPROVAL`. It correctly flagged synthetic quotes, a historical requested date and a budget read rejected by ERP permissions. The human explicitly approved the USD 370 SafetyFirst demo order, Net 30, delivery November 2, 2026, accepting those warnings. Approval is recorded through the real API with that justification.

Model arithmetic is independently checked: quote scores are recomputed using the documented 35/30/20/15 weights and neutral unknown history. Quote IDs and eligible supplier selection are checked against current evidence. The cheapest fixture scores 66, not the model's unverified 73.91. Approved quotes bind supplier, prices, payment terms and delivery date at the ERP write boundary. Completed requests are rejected before another job is queued.

Reference: [Groq Qwen mode selection](https://console.groq.com/docs/model/qwen/qwen3.8-27b).

## Verified local purchase order and duplicate protection

The first model-driven PO attempt (`2569f973-7783-4574-a6e8-058625078bb1`) failed on a provider connection error before a write claim existed. The operator checked that ERP contained no linked order and the approved snapshot was unchanged before recovering the existing approval. No write claim was deleted and no approval was fabricated.

Quote-backed PO execution now uses a typed deterministic executor after the model sourcing/analysis and human decision. It validates current quote eligibility, invokes the guarded create operation exactly once, and reads the ERP order back. Other PO cases retain the model-planned path and are not established by this test.

Successful resumed job: `ea7b447d-ff79-4b40-903b-3a1f171fc60a`.

- ERP order: `PUR-ORD-2026-00001`; submitted, status `to_receive`.
- Supplier: SafetyFirst Equipment Co; USD 370; Net 30.
- Items: 20 × `MAT-SF-001` at 11.50 and 10 × `MAT-SF-002` at 14.00.
- Order date: October 26, 2026. Delivery: November 2, 2026.
- Both ERP lines link to `MAT-MR-2026-00001`.
- Permanent write claim: `verified`, carrying the real ERP order ID.
- Duplicate API attempt: HTTP 409; exactly one linked order before and after.

[Captured ERP and duplicate evidence](evidence/2026-10-26-procurement.json). This establishes the narrow local quote-backed procurement path. It does not establish production hardening, a public backend, live invoice/payment completion or unattended success for arbitrary tasks.

## Chat provider timeout boundary

An additional read-only chat smoke request timed out at the HTTP client. A bounded follow-up returned a controlled error in approximately three seconds; provider logs identified Groq HTTP 429 on the daily token allowance (200000 limit, 197990 used, 2521 requested). Chat now disables nested provider retries, uses a 20-second request timeout and a six-turn cap, and returns a clear incomplete-request error instead of exposing raw provider output. The successful core procurement evidence is separate from this check; natural-language chat is not required to repeat the captured PO demonstration.

## Backup capture

A local backup was created after PO verification in ignored private directory `backups/20261026T050126Z/`: application PostgreSQL export, Keycloak database export, ERPNext database/files and document volume. Both application and ERP database exports contain `PUR-ORD-2026-00001`. This is a backup capture check, not a restoration drill. Preserve private credentials separately and copy the backup off the laptop before deleting Docker volumes.

The Netlify architecture-preview production build passed with both backend public URLs intentionally unset. The local Vite configuration retains its localhost URLs; those are correctly rejected by the Netlify deployment guard when used for a public build. Local preflight including the Docker engine passed.
