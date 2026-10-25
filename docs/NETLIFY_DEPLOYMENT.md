# CentrAlign AI — deployment guide

## Hosting constraint

The frontend can use Netlify's free plan within its limits. **No verified strictly free, always-online host suitable for this complete ERPNext + databases + identity + agent worker stack has been established.** This guide prepares that stack; it does not claim a free public backend has been provisioned.

Current published limitations explain why the common free web hosts are not substitutes:

| Service | Relevant limitation | Suitability for this stack |
| --- | --- | --- |
| Netlify | Function duration limits; no persistent Docker/ERP services | Frontend only |
| Render free web service | Sleeps after inactivity; no persistent disk | Cannot preserve ERPNext/MariaDB locally or keep the worker always running |
| Koyeb free instance | Scales to zero after inactivity; free instances cannot attach a volume | Cannot meet the persistent always-online requirement |
| Hugging Face Spaces | Current compute eligibility/plan restrictions; ephemeral disk and sleep behavior | Not an established free backend host for this stack |

Sources checked October 24–25, 2026: [Netlify functions](https://docs.netlify.com/build/functions/configuration/), [Render free services](https://render.com/docs/free), [Koyeb instances](https://www.koyeb.com/docs/reference/instances), [Koyeb volumes](https://www.koyeb.com/docs/reference/volumes), [Spaces overview](https://huggingface.co/docs/hub/spaces-overview).

Trials, startup credits, and a free database account are not equivalent to permanent hosting for all these services. With Oracle and AWS excluded, full public deployment remains conditional on a suitable host or donated compute. Do not use artificial keep-alive traffic as a replacement for an eligible service.

## 1. Prepare the repository and private configuration

Commands below run at the repository root. Install Docker with Compose v2 supporting `include`, Python 3.13, and Node.js 22. Start the Docker daemon.

```sh
make init
```

This creates random secrets in `.env` and an empty `secrets/erp-users.json`. Existing `.env` files are not overwritten. Both paths are ignored by Git. Add your provider configuration locally:

```dotenv
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=YOUR_OWN_KEY
```

Groq is the default compatible endpoint, not a guarantee that this model or quota is free for your account. Check your provider dashboard. For Gemini, use `LLM_PROVIDER=gemini`, its supported model ID and your own key. For Ollama, use `LLM_PROVIDER=ollama`, a locally installed tool-capable model ID, and a reachable `OLLAMA_HOST`; this moves inference to your own compute. No Bedrock fallback is used.

Keep the generated values for `SERVICE_SECRET`, database passwords and identity passwords. Never put them in frontend variables, commit them, or paste them into deployment logs.

Validate Compose before starting services:

```sh
docker compose --env-file .env.example config --quiet
```

This validates syntax; it does not start or test the containers.

For image-build failures, see [Docker troubleshooting](DOCKER_TROUBLESHOOTING.md). The API, worker and bootstrap roles share one runtime image, built through `docker compose build api`.

## 2. Bootstrap the backend in a local test environment

```sh
make bootstrap
```

The script builds the API/worker image, starts ERPNext, MariaDB, Redis, PostgreSQL and Keycloak, creates the ERP site `aria.local` once, then configures identity and ERP users.

The first run stops when the ERP company is missing. Open `http://localhost:8080`, sign in as `Administrator` with the `ERPNEXT_PASSWORD` from your private `.env`, and complete the ERPNext setup wizard with:

- Company: `Apex Manufacturing Group`
- Abbreviation: `AMG`
- Country: `United States`
- Currency: `USD`
- A fiscal year that includes your test dates

Confirm the default `Stores - AMG` warehouse and chart of accounts exist. Then rerun:

```sh
make bootstrap
```

Bootstrap configures:

- Keycloak realm `aria`, public client `aria-web`, PKCE, API audience `aria-api`, role and department claims.
- ERP users matching the upstream demo personas, with their own ERP roles and API keys. No broad service-account fallback is used by the app.
- Demo supplier/item/requisition data. A private `seed-complete` marker prevents accidental reseeding on later bootstrap runs.
- The FastAPI service and one worker replica.

The seed data contains historical scenario dates. For a current demonstration, create a new requisition through the app with valid current dates. Do not assume a historical fixture must still qualify for auto-approval.

For initial UI testing:

```sh
cp frontend/.env.example frontend/.env
npm ci --prefix frontend
npm run dev --prefix frontend
```

The example frontend configuration uses `http://localhost:8000/api` and `http://localhost:8081/realms/aria`. Open Vite's printed local URL. Sign in with a demo email such as `demo+jake@example.com` for procurement, `demo+sarah@example.com` for approval, or `demo+priya@example.com` for AP. The initial Keycloak password is `ERPNEXT_USER_PASSWORD`; Keycloak requires a password change on first login. ERP API access uses separate generated keys and does not depend on that browser password.

Keycloak administration is at `http://localhost:8081/admin`, username `admin`, password `KEYCLOAK_ADMIN_PASSWORD`. To test writes above 50000 or reconcile interrupted jobs, assign the application `admin` realm role to the intended ERP-provisioned identity. An application role does not grant ERP permissions that its ERP user lacks.

## 3. Validate a real workflow before public hosting

```sh
curl http://localhost:8000/api/health
make logs
```

The health endpoint confirms API availability only. Test all of the following with synthetic data:

1. Unauthenticated API calls fail and sign-in returns the correct role.
2. A new requisition goes through sourcing and analysis; human approval resumes PO generation when required.
3. The PO appears in ERPNext with matching supplier, line quantities and rates. Capture the order ID and run history.
4. A repeated PO attempt is rejected. An unavailable model returns a failure rather than success.
5. A worker interruption leaves the document blocked until reconciliation.
6. An invoice upload reaches review without creating an ERP record; confirmation creates the expected invoice once.
7. Payment tests include submitted receipts and an ERP bank/cash account, valid Mode of Payment and open accounting period. Missing receipts or mismatched balances must block payment.

Provider quotas may require a smaller workflow or different model. Record the model and outcomes in your submission; do not claim measured reliability without running these checks.

## 4. Create the Netlify frontend site

Before publishing, run `npm ci --prefix frontend`, then `npm run build:netlify --prefix frontend`. The frontend lockfile is included in the repository; Netlify and CI use it with `npm ci` for reproducible installation.

Push the prepared repository to your own GitHub account, retaining the license and upstream provenance. In Netlify, choose **Add new project → Import an existing project**, select the repository, and use the root `netlify.toml`:

- Base directory: `frontend`
- Build command: `npm run build:netlify`
- Publish directory: `frontend/dist` relative to the repository, or `dist` relative to the base directory
- Node.js: `22`

The config already sets base `frontend` and publish `dist`. A frontend-only preview can build without backend variables and displays a setup message at sign-in. It is not a working agent deployment.

Use the site's assigned `https://YOUR-SITE.netlify.app` URL as its production origin. Deploy previews have separate origins and require explicit CORS/OIDC configuration; production configuration does not automatically authorize every preview.

## 5. Connect a backend host when one is available

The backend host needs Docker, persistent volumes, enough memory/disk for ERPNext and Keycloak, and inbound HTTPS. Determine resources through measurement; this stack is not designed for a tiny serverless free instance.

Copy the source and private configuration securely to the host. Do not publish ERPNext, PostgreSQL, MariaDB, Redis, or API management ports directly. The Compose file binds development/admin ports to loopback.

Use public DNS names you control for API and identity, then set root `.env`:

```dotenv
FRONTEND_ORIGIN=https://YOUR-SITE.netlify.app
API_DOMAIN=api.YOUR-DOMAIN
AUTH_DOMAIN=auth.YOUR-DOMAIN
KEYCLOAK_HOSTNAME=https://auth.YOUR-DOMAIN
OIDC_ISSUER=https://auth.YOUR-DOMAIN/realms/aria
```

Point those DNS names to the host and allow ports 80/443 for Caddy and certificate issuance. This step assumes eligible DNS names and a reachable host; neither has been purchased or provisioned by this repository setup.

Run bootstrap on that host. For the private ERP setup wizard or Keycloak administration, use an SSH tunnel, for example:

```sh
ssh -L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081 USER@BACKEND_HOST
```

If Keycloak's public hostname is already set, access its administration through that public HTTPS hostname rather than the local tunnel URL. Complete the ERP wizard through the ERP tunnel, then rerun bootstrap. Start the public proxy:

```sh
docker compose --profile public up -d
```

Bootstrap uses Keycloak's internal endpoint for administration, but issued tokens use the configured public issuer. Rerun bootstrap after changing `FRONTEND_ORIGIN` so the exact redirect URI and web origin are updated. Existing user passwords and ERP API keys are preserved.

Set these **public** Netlify environment variables and redeploy:

```dotenv
VITE_API_URL=https://api.YOUR-DOMAIN/api
VITE_OIDC_AUTHORITY=https://auth.YOUR-DOMAIN/realms/aria
VITE_OIDC_CLIENT_ID=aria-web
```

Do not add `LLM_API_KEY`, ERP API keys or database passwords to Netlify. Vite variables are embedded in the browser bundle. API requests go directly from the browser to the backend, with OIDC bearer tokens. The backend CORS origin and Keycloak client redirect URI must exactly match your Netlify site.

## 6. Operations and recovery

```sh
make logs
make backup
```

The backup script exports application and Keycloak PostgreSQL databases, ERP database/files and uploaded documents into a private timestamped directory. Copy backups off-host, and preserve `.env` plus the ERP credential mapping separately. Backups on the same host do not protect against host loss.

For restoration, use the same image versions: stop API/worker/Keycloak, restore `aria.sql` and `keycloak.sql` into their respective PostgreSQL databases, restore ERP's database and public/private files using `bench --site aria.local restore ... --with-public-files ... --with-private-files ...`, restore the documents archive with ownership for UID 10001, restore the original credentials, and restart the services. Validate identity and all workflow records before accepting writes. This is a procedure to rehearse on a disposable host, not a tested restore guarantee.

Interrupted job reconciliation: an app admin may call `POST /api/agents/runs/JOB_ID/reconcile` with an `evidence` string after inspecting ERP. This releases the job lock only. Permanent entries in the SQL `records` collection `write-claims` remain blocked until an operator has reconciled the actual ERP outcome. Do not delete claims just to make a retry pass. The prototype deliberately has no one-click write-claim reset.

`docker compose down` keeps named volumes. `docker compose down -v` deletes databases and documents; it is not an ordinary restart command.
