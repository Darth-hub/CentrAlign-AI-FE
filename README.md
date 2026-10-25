# ARIA portable procurement operator

An AWS-free adaptation of [AWS Samples' ARIA procure-to-pay project](https://github.com/aws-samples/sample-multi-agent-procure-to-pay). This repository retains the upstream domain agents and UI, and replaces the managed AWS execution, authentication, storage and model integration. See [UPSTREAM.md](UPSTREAM.md) for provenance and [docs/MIGRATION.md](docs/MIGRATION.md) for the differences.

The frontend targets **Netlify**. FastAPI, the agent worker, Keycloak, ERPNext, MariaDB, Redis and PostgreSQL require a persistent Docker host. A strictly free, always-online backend host suitable for this entire stack has **not** been established. The Netlify frontend can be published separately, but that does not deploy a working ERP or autonomous worker.

## What this implementation does

- Understands procurement requests through chat and specialized agents using Strands.
- Runs sourcing → requisition analysis → approval → purchase order creation with real ERPNext operations.
- Stores jobs, progress events, conversation history, workflow state and human decisions in SQL.
- Binds agent operations to the verified user's ERP credentials and permissions.
- Requires an unchanged approved requisition before PO creation; verifies the resulting ERP record independently of generated text.
- Rejects duplicate PO/payment attempts, preserves uncertain write claims, and requires reconciliation following an interruption.
- Extracts invoice PDFs/images, presents the values for human confirmation, then creates and reads back the ERP invoice.
- Checks receipt quantities, invoice prices and outstanding balance before a human-confirmed payment entry.

This is a prototype migration, not a claim of production parity with AWS AgentCore. The implemented procurement write scope is one complete PO per requisition. Split awards, receipt returns, multiple-PO invoices and arbitrary Python execution require manual handling. Model risk scores are advisory. See the migration document for other limits.

## Setup

1. Read [the deployment guide](docs/NETLIFY_DEPLOYMENT.md), especially the hosting constraint.
2. Install Docker with Compose v2, Node.js 22 and Python 3.13.
3. Run `make init`, then add your own model key to the private root `.env`.
4. Start Docker and run `make bootstrap`. Complete the ERPNext company setup wizard when prompted, then run it again.
5. For local UI development, copy `frontend/.env.example` to `frontend/.env`, run `npm install --prefix frontend`, then `npm run dev --prefix frontend`.
6. For Netlify, follow the public URL, OIDC and CORS setup in the deployment guide.

Supported model providers are `groq`, `gemini`, `openai-compatible` and `ollama`. Provider free tiers have quotas and availability conditions; they do not provide the ERP/backend hosting. Model keys belong only on the backend.

The original AWS frontend lockfile is archived under `docs/upstream/`. Regenerate `frontend/package-lock.json` with `npm install --prefix frontend` and commit it after a successful build. Registry connectivity prevented lockfile regeneration and frontend compilation during this migration.

## Validation

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
make test
npm install --prefix frontend
npm run build:netlify --prefix frontend
docker compose --env-file .env.example config --quiet
```

The portable test suite uses temporary SQLite and fake ERP/model boundaries. It checks authentication, authorization, durable jobs, write guards, approval snapshots, document review and fabricated completion claims. It does not substitute for a live ERP/model deployment test. Historical tests under `backend/tests`, the original AWS deployment under `infra`, and the original local harness under `local` are retained as upstream reference and are not the active deployment path.

Keep `LICENSE` and `THIRD-PARTY-LICENSES.md` with the repository. Describe your own migration and additions accurately when presenting the project.
