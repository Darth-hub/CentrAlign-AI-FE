# Demonstration and evidence runbook

Use a disposable company and synthetic records. This is a planned demonstration, not a claim that live integration already passed.

## Before Docker is ready

- Run `make preflight`, `make test`, and `npm run test:config --prefix frontend`.
- Build the frontend and review `/architecture` without signing in.
- Explain the separation between identity, queued execution, domain agents, ERP tools and persistent evidence using the architecture map.
- Prepare a fresh requisition using an existing seeded item and supplier, valid current dates and a quantity/rate you can independently check. Do not promise that historical seed dates meet current policies.
- Choose a tool-capable model available to your provider account. Record the provider/model name, never the key.

## After bootstrap succeeds

1. Confirm `curl http://localhost:8000/api/health` succeeds. This checks API availability, not the full workflow.
2. Open the frontend and sign in as procurement (`demo+jake@example.com`). Use the initial password from private configuration and complete the required password change.
3. Create a fresh requisition in the requisitions view. Note its document ID, item, quantity, expected rate and company.
4. Select that requisition and start its full workflow. Show actual progress and run history instead of describing future actions.
5. If approval is required, sign in as the designated approver (`demo+sarah@example.com`), inspect the request and record the real decision. Resume through the app's workflow controls.
6. Inspect the resulting PO in ERPNext. Match its originating requisition, supplier, items, quantities and rates to the request and approval snapshot.
7. Refresh the frontend and show the persisted history and order ID.
8. Attempt the workflow again for the same completed requisition. Confirm no additional PO is created. If any result is uncertain, inspect ERP before retrying.

## Additional reliability scenarios

| Scenario | Expected behavior | Evidence to capture |
| --- | --- | --- |
| Unauthenticated request | Protected operations rejected | HTTP response without a bearer token |
| Provider unavailable | Run reports failure rather than fabricated success | Failed run and absence of an unexpected ERP write |
| Worker interruption | Work remains blocked pending reconciliation | Interrupted job, retained lock and ERP inspection |
| Invoice upload | Extracted values wait for confirmation before ERP creation | Review screen, confirmed invoice ID and ERP read-back |

Run interruption/provider-failure scenarios only in the disposable environment after the successful path. Do not delete write claims to force retries. See the deployment guide's recovery procedure.

## Suggested 4–5 minute recording

- 30 seconds: user objective and architecture.
- 30 seconds: actual requisition and expected result.
- 2 minutes: execution and required human decision; if accelerated, label time cuts.
- 1 minute: independently inspect the ERP PO and persisted run history.
- 30 seconds: duplicate protection, limitations and remaining deployment work.

If an execution takes longer, record it honestly and edit waiting time visibly. Do not substitute sample data or a simulated result for real execution.

## Evidence record template

```text
Date:
Git commit:
Environment (local/public):
Provider and model:
Request / requisition ID:
Run ID:
Human decision (if required):
ERP purchase order ID:
Expected vs actual supplier, items, quantities and rates:
Duplicate attempt result:
Observed failures / unresolved limitations:
Demo recording URL:
```

Do not include passwords, bearer tokens, model keys or ERP API keys in screenshots or recordings.
