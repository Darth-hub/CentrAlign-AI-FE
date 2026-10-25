# Validation and delivery status

Last checked: October 25, 2026.

| Area | Status | Evidence or next step |
| --- | --- | --- |
| Repository | Published | `Darth-hub/CentrAlign-AI-FE` |
| Backend runtime tests | 18 passing locally | `make test`; temporary SQLite and controlled ERP/model boundaries |
| Python source | Compiles | `python -m compileall -q backend scripts` |
| Compose definition | Validated | `docker compose --env-file .env.example config --quiet` |
| Bootstrap and backup scripts | Shell syntax checked | `bash -n scripts/bootstrap.sh scripts/backup.sh` |
| Frontend | Production build passed locally | TypeScript + Vite; generated dependency lockfile included |
| Live identity and ERP workflow | Integration pending | Start Docker, configure a model, bootstrap the tenant and exercise a full request |
| Invoice OCR | Integration pending | Validate Tesseract and representative PDFs/images |
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
