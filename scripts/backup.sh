#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
backup_dir="backups/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"
docker compose exec -T postgres pg_dump -U aria aria > "$backup_dir/aria.sql"
docker compose exec -T postgres pg_dump -U aria keycloak > "$backup_dir/keycloak.sql"
docker compose exec -T backend bench --site aria.local backup --with-files
docker compose cp backend:/home/frappe/frappe-bench/sites/aria.local/private/backups "$backup_dir/erpnext"
docker compose exec -T api tar -C /data -czf - documents > "$backup_dir/documents.tar.gz"
echo "Backup written to $backup_dir. Copy it off-host; preserve secrets separately."
