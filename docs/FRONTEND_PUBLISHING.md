# Publish the frontend while backend setup is pending

This publishes a real frontend and architecture page. Agent execution becomes available only after a reachable backend and identity service are connected.

## Local checks

From the repository root:

```sh
make preflight
npm ci --prefix frontend
npm run test:config --prefix frontend
npm run build:netlify --prefix frontend
```

`build:netlify` reads production Vite environment files as well as build-service variables. If `frontend/.env` contains local HTTP URLs for development, use `npm run build --prefix frontend` for a local-only build. Netlify builds from Git, where private `.env` files must remain untracked. Do not change local development URLs to arbitrary public placeholders just to pass the deployment check.

## Netlify setup

1. Sign in to your own Netlify account.
2. Import `Darth-hub/CentrAlign-AI-FE`, branch `main`.
3. Let the checked-in `netlify.toml` configure base `frontend`, build `npm run build:netlify`, publish `dist`, and Node.js 22.
4. For an architecture-only preview, leave `VITE_API_URL` and `VITE_OIDC_AUTHORITY` unset. Set neither model keys nor service secrets in Netlify.
5. Deploy, then save the assigned HTTPS site URL.
6. Open `/`, select **Explore the architecture and execution workflow**, and check the diagram. Refresh `/architecture` directly to check SPA routing.
7. Check that sign-in is disabled and the missing-configuration message is visible. No live ERP data should be shown in this state.

Only claim a frontend preview at this stage. Do not label it a functioning autonomous operator until a real workflow succeeds.

## Connect the runtime later

Follow [NETLIFY_DEPLOYMENT.md](NETLIFY_DEPLOYMENT.md), including backend CORS and Keycloak redirect configuration. Then set these public Netlify variables and redeploy:

```dotenv
VITE_API_URL=https://YOUR-API-HOST/api
VITE_OIDC_AUTHORITY=https://YOUR-AUTH-HOST/realms/aria
VITE_OIDC_CLIENT_ID=aria-web
```

Both service URLs must be configured together. Private provider, ERP and database credentials stay on the backend host. A Netlify frontend cannot use `localhost` to reach your laptop on behalf of remote visitors.

## Acceptance checklist

- [ ] Build completes from the GitHub repository.
- [ ] Root page displays CentrAlign AI.
- [ ] Architecture link and image work on desktop and mobile.
- [ ] Direct refresh of `/architecture` works.
- [ ] Preview visibly indicates that sign-in needs backend configuration.
- [ ] Once connected: real identity login, backend access and verified ERP result pass.

Unchecked items are work to perform, not a record of completed validation.
