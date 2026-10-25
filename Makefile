.PHONY: init build up down logs bootstrap test frontend backup preflight
init:
	python3 scripts/init-env.py
build:
	docker compose build api
up:
	docker compose up -d
bootstrap:
	bash scripts/bootstrap.sh
down:
	docker compose down
logs:
	docker compose logs --tail=100 -f api worker
test:
	.venv/bin/python -m pytest -c backend/pytest-portable.ini backend/tests_portable
frontend:
	cd frontend && npm ci && npm run build
backup:
	bash scripts/backup.sh

preflight:
	python3 scripts/preflight.py
