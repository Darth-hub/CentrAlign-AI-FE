#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f .env || { echo 'Run make init, then configure .env'; exit 1; }
# All application services share the image built by api.
docker compose build api
# Repair partial first-time initialization before starting identity. A .sql
# mount avoids executable-script restrictions on macOS shared filesystems.
docker compose up -d --wait --wait-timeout 120 postgres
docker compose exec -T postgres sh -c 'psql -q -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --file=/docker-entrypoint-initdb.d/01-keycloak.sql'
docker compose up -d db redis backend frontend websocket queue-short scheduler keycloak
# The initialization container makes the site once; a repeat run preserves it.
docker compose exec -T -e ERPNEXT_PASSWORD="$(python3 -c "from pathlib import Path; print(dict(l.split('=',1) for l in Path('.env').read_text().splitlines() if l and not l.startswith('#'))['ERPNEXT_PASSWORD'])")" \
  -e MYSQL_ROOT_PASSWORD="$(python3 -c "from pathlib import Path; print(dict(l.split('=',1) for l in Path('.env').read_text().splitlines() if l and not l.startswith('#'))['MYSQL_ROOT_PASSWORD'])")" \
  backend bash -c 'if [ ! -f sites/aria.local/site_config.json ]; then bench new-site aria.local --mariadb-user-host-login-scope="%" --db-root-password "$MYSQL_ROOT_PASSWORD" --admin-password "$ERPNEXT_PASSWORD" --install-app erpnext; fi'
docker compose run --rm bootstrap
docker compose up -d api worker
echo 'Backend prepared. Configure Netlify public URLs after selecting the backend host.'
