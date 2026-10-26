# Validation and delivery status

Last checked: October 26, 2026.

| Area | Status | Evidence or next step |
| --- | --- | --- |
| Repository | Published | `Darth-hub/CentrAlign-AI-FE` |
| Backend runtime tests | 31 passing locally | `make test`; temporary SQLite and controlled ERP/model boundaries |
| Python source | Compiles | `python -m compileall -q backend scripts` |
| Compose definition | Validated | `docker compose --env-file .env.example config --quiet` |
| Bootstrap and backup scripts | Shell syntax checked | `bash -n scripts/bootstrap.sh scripts/backup.sh` |
| Frontend | Production build passed locally | TypeScript + Vite; generated dependency lockfile included |
| Identity startup and bootstrap | Verified locally | Keycloak database repair, discovery and realm/client/user configuration succeeded |
| Live ERP workflow | Integration pending | Complete the company wizard, finish tenant bootstrap and exercise a full request |
| Docker runtime image | Built locally on arm64 | Shared Python 3.13 Bookworm image; API/worker/bootstrap use the same tag |
| OCR runtime dependencies | Container smoke checks passed | Synthetic image and raster PDF recognized through Pillow/PDFium + Tesseract; fixtures present; pip check passed |
| Invoice extraction workflow | Integration pending | Validate representative invoices, model extraction, review and ERP creation |
| Deployment configuration | 6 tests passing locally | Env-file loading, secret rejection, paired configuration and HTTPS/loopback checks |
| Setup check | Passed locally, Docker probe skipped | `make preflight`; no credentials printed |
| Public architecture preview | Implemented | `/architecture` is available without an organization login |
| Public application | Not deployed | Netlify frontend configuration exists; persistent backend host is unresolved |
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
