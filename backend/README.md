# CentrAlign AI backend

FastAPI provides the control plane. A persistent worker executes domain agents in isolated processes. The canonical adapter connects permitted actions to ERPNext using each acting user's credentials.

![Architecture](../docs/assets/centralign-architecture.svg)

## Entry points

| Path | Responsibility |
| --- | --- |
| `main.py` | API, verified identity middleware, roles and CORS |
| `api/runs.py` | Start jobs, poll events and reconcile interrupted work |
| `runtime/jobs.py` | Durable SQL queue, owner checks and document locks |
| `runtime/worker.py` | Claim jobs, run subprocesses, persist results and enforce deadlines |
| `runtime/runner.py` | Bind verified identity and execute the selected job |
| `agentcore_app.py` | Procurement orchestration; the filename is retained as an internal entry point |
| `runtime/tools.py` | Typed ERP operations and bounded arithmetic |
| `services/write_policy.py` | Approval snapshots, write claims and ERP completion evidence |
| `adapters/canonical_api.py` | Canonical HTTP API and shared tool dispatcher |

## HTTP surface

- `GET /api/health` — API availability.
- `POST /api/agents/{agent}/runs` — queue a supported procurement analysis or workflow.
- `GET /api/agents/runs/{job_id}/events?after=...` — poll ordered progress and results.
- `POST /api/agents/runs/{job_id}/reconcile` — admin reconciliation after inspecting ERP.
- `/api/agents/chat`, `/api/chat/` — conversational intake and persisted sessions.
- `/api/decisions/` — human approval and rejection.
- `/api/invoices/` — extraction, proposal review, confirmation and payment actions.
- `/api/erp/` — canonical procurement operations mounted by the API.

All protected requests require a verified identity. The browser cannot choose a different acting user through a request header or body.

## Local execution

Use root `make init` and `make bootstrap` for the configured Docker services. Manual process commands, from `backend/` with the required environment set, are `uvicorn main:app --host 0.0.0.0 --port 8000` and `python -m runtime.worker`.

Run the focused test suite from the repository root with `make test`. PostgreSQL is the deployment database; tests use temporary SQLite. The suite under `tests_portable/` is the active runtime suite. Historical tests are separate references.

[Architecture](../docs/ARCHITECTURE.md) · [Implementation](../docs/IMPLEMENTATION.md) · [Deployment](../docs/NETLIFY_DEPLOYMENT.md)
