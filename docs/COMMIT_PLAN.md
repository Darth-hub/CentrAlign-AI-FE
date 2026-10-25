# 25-commit publication plan

Commit 1 preserves GitHub’s initial README. The remaining 24 commits import the reviewed source in batches. Upstream provenance is retained. Create each new commit when its batch is reviewed; changing push times does not change commit dates. Intermediate imports are not independently runnable; the complete snapshot is the application validation target.

## 01. Initial commit (existing GitHub README)

- `README.md`

## 02. docs: preserve upstream provenance and repository guidance

- `LICENSE`
- `THIRD-PARTY-LICENSES.md`
- `UPSTREAM.md`
- `.bandit`
- `.gitignore`
- `.gitleaks.toml`
- `.pre-commit-config.yaml`
- `.semgrepignore`
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `SECURITY.md`

## 03. chore: retain original AWS architecture and infrastructure references

- `backend/README.md`
- `backend/adapters/README.md`
- `backend/agents/README.md`
- `docs/ARCHITECTURE.md`
- `docs/assets/ARIA-architecture.svg`
- `docs/assets/arch-transparent.png`
- `docs/assets/arch-white-background.png`
- `docs/assets/aria-chat.gif`
- `docs/assets/aria-dfd.png`
- `docs/assets/login-bg.mp4`
- `docs/assets/logo-banner.png`
- `docs/assets/logo.png`
- `docs/upstream/README-AWS.md`
- `docs/upstream/frontend-package-lock-AWS.json`
- `infra/.gitignore`
- `infra/README.md`
- `infra/bin/app.ts`
- `infra/bin/e2e.ts`
- `infra/cdk.context.example.json`
- `infra/cdk.json`
- `infra/docker/docker-compose.ecs-test.yaml`
- `infra/docker/docker-compose.local-test.yaml`
- `infra/docker/docker-compose.yaml`
- `infra/docker/env-erpnext`
- `infra/docker/setup-site.sh`
- `infra/lambda/pre_token_generation/handler.py`
- `infra/lib/erpnext-stack.ts`
- `infra/lib/openapi/p2p-tools.json`
- `infra/lib/p2p-agentic-stack.ts`
- `infra/lib/p2p-auth-e2e-stack.ts`
- `infra/lib/p2p-auth.ts`
- `infra/lib/p2p-policy.ts`
- `infra/package-lock.json`
- `infra/package.json`
- `infra/policies/p2p-procurement.cedar`
- `infra/scripts/deploy-frontend.sh`
- `infra/scripts/generate-tools-schema.py`
- `infra/tests/e2e/requirements.txt`
- `infra/tests/e2e/run_e2e.py`
- `infra/tests/requirements.txt`
- `infra/tests/test_cedar_policies.py`
- `infra/tests/test_role_authorization.py`
- `infra/tsconfig.json`

## 04. data: retain the local harness and ERPNext demo fixtures

- `local/Makefile`
- `local/README.md`
- `local/config/harness_env.py`
- `local/config/local-config.js`
- `local/env.example`
- `local/scripts/init_aws.py`
- `local/scripts/seed_local.py`
- `local/shims/agent_proxy_shim.py`
- `local/shims/agentcore_shim.py`
- `local/shims/canonical_api_shim.py`
- `local/shims/mcp_gateway_shim.py`
- `local/shims/run_agent.py`
- `local/supervisor.py`
- `utilities/.env.example`
- `utilities/README.md`
- `utilities/requirements.txt`

## 05. chore: retain ERPNext setup and simulation utilities

- `utilities/scripts/01_verify_erpnext.py`
- `utilities/scripts/02_setup_users.py`
- `utilities/scripts/03_setup_erpnext_oauth.py`
- `utilities/scripts/04_seed_demo_data.py`
- `utilities/scripts/05_verify_demo_data.py`
- `utilities/scripts/06_reset_demo.py`
- `utilities/scripts/07_nuke_all_data.py`
- `utilities/scripts/ERPNEXT_COGNITO_SSO.md`
- `utilities/scripts/add_license_headers.py`
- `utilities/scripts/config.py`
- `utilities/scripts/erpnext_client.py`
- `utilities/simulation/README.md`
- `utilities/simulation/__init__.py`
- `utilities/simulation/api_client.py`
- `utilities/simulation/config.py`
- `utilities/simulation/lambda_handler.py`
- `utilities/simulation/llm_generator.py`
- `utilities/simulation/simulator.py`
- `utilities/simulation/state_manager.py`

## 06. feat: import canonical ERP contracts and historical tests

- `backend/tests/__init__.py`
- `backend/tests/conftest.py`
- `backend/tests/fixtures/goods_receipts.json`
- `backend/tests/fixtures/invoices.json`
- `backend/tests/fixtures/materials.json`
- `backend/tests/fixtures/purchase_orders.json`
- `backend/tests/fixtures/purchase_requisitions.json`
- `backend/tests/fixtures/vendors.json`
- `backend/tests/test_agent_prompts.py`
- `backend/tests/test_agentcore.py`
- `backend/tests/test_agents.py`
- `backend/tests/test_api_routes.py`
- `backend/tests/test_automated_reasoning.py`
- `backend/tests/test_canonical_api.py`
- `backend/tests/test_canonical_models.py`
- `backend/tests/test_erp_auth.py`
- `backend/tests/test_erpnext_adapter.py`
- `backend/tests/test_field_maps.py`
- `backend/tests/test_services.py`
- `backend/tests/test_textract.py`
- `backend/tests/test_workflow.py`
- `backend/adapters/__init__.py`
- `backend/adapters/erp_adapter_base.py`
- `backend/adapters/errors.py`
- `backend/adapters/models.py`

## 07. feat: configure ERP mappings HTTP timeouts and user credentials

- `backend/adapters/erpnext/__init__.py`
- `backend/adapters/erpnext/field_maps.py`
- `backend/adapters/erpnext/client.py`
- `backend/adapters/erpnext/oauth.py`

## 08. feat: integrate ERPNext operations with the canonical API

- `backend/adapters/erpnext/adapter.py`
- `backend/adapters/canonical_api.py`

## 09. feat: configure non-AWS models and SQL persistence

- `backend/config.py`
- `backend/config/__init__.py`
- `backend/config/procurement_policy.md`
- `backend/providers/__init__.py`
- `backend/requirements-dev.txt`
- `backend/requirements.lock.txt`
- `backend/requirements.txt`
- `backend/services/__init__.py`
- `backend/services/database.py`
- `backend/services/dynamo.py`
- `backend/services/exceptions.py`

## 10. feat: verify identities and maintain procurement lifecycle context

- `backend/security/__init__.py`
- `backend/security/routes.py`
- `backend/services/auth.py`
- `backend/services/contracts.py`
- `backend/services/lifecycle.py`

## 11. feat: run durable agent jobs in isolated worker processes

- `backend/runtime/__init__.py`
- `backend/runtime/jobs.py`
- `backend/runtime/runner.py`
- `backend/runtime/worker.py`

## 12. feat: restrict agent tools and verify ERP write outcomes

- `backend/runtime/tools.py`
- `backend/utils/__init__.py`
- `backend/utils/mcp_client.py`
- `backend/utils/progress_hooks.py`
- `backend/services/erp_client.py`
- `backend/services/write_policy.py`

## 13. feat: extract invoice documents into reviewable proposals

- `backend/services/storage.py`
- `backend/services/textract.py`

## 14. feat: adapt upstream procurement domain agents

- `backend/agents/__init__.py`
- `backend/agents/invoice_matching_agent.py`
- `backend/agents/p2p_workflow.py`
- `backend/agents/payment_agent.py`
- `backend/agents/po_management_agent.py`
- `backend/agents/receiving_agent.py`
- `backend/agents/requisition_agent.py`
- `backend/agents/sourcing_agent.py`

## 15. feat: bind conversational procurement to verified users and SQL

- `backend/agents/chat_agent.py`
- `backend/api/agents.py`
- `backend/api/chat.py`
- `backend/services/rate_limiter.py`

## 16. feat: orchestrate sourcing approval and verified purchase orders

- `backend/agentcore_app.py`
- `backend/api/workflows.py`
- `backend/workflow/__init__.py`
- `backend/workflow/orchestrator.py`

## 17. feat: expose persistent runs invoice review and procurement APIs

- `backend/api/__init__.py`
- `backend/api/admin.py`
- `backend/api/config_view.py`
- `backend/api/dashboard.py`
- `backend/api/decisions.py`
- `backend/api/errors.py`
- `backend/api/invoices.py`
- `backend/api/lifecycle.py`
- `backend/api/runs.py`
- `backend/main.py`

## 18. test: verify portable runtime auth recovery and ERP write guards

- `backend/pytest-portable.ini`
- `backend/tests_portable/conftest.py`
- `backend/tests_portable/test_runtime.py`

## 19. build: package persistent backend services with Docker Compose

- `.dockerignore`
- `.env.example`
- `Makefile`
- `backend/Dockerfile`
- `compose.yaml`
- `deploy/Caddyfile`
- `deploy/compose.erp.yaml`
- `deploy/init-postgres.sh`
- `scripts/backup.sh`
- `scripts/bootstrap.py`
- `scripts/bootstrap.sh`
- `scripts/init-env.py`

## 20. build: configure the React frontend and shared application assets

- `frontend/.env.example`
- `frontend/.gitignore`
- `frontend/README.md`
- `frontend/eslint.config.js`
- `frontend/index.html`
- `frontend/package.json`
- `frontend/public/arch-diagram.png`
- `frontend/public/arch-diagram.svg`
- `frontend/public/backend-not-configured.json`
- `frontend/public/favicon.svg`
- `frontend/public/login-bg.mp4`
- `frontend/public/vite.svg`
- `frontend/src/ThemeContext.tsx`
- `frontend/src/assets/react.svg`
- `frontend/src/i18n.ts`
- `frontend/src/index.css`
- `frontend/src/lib/utils.ts`
- `frontend/src/locales/en/translation.json`
- `frontend/src/lookups.ts`
- `frontend/src/main.tsx`
- `frontend/src/roles.ts`
- `frontend/src/types/p2p.ts`
- `frontend/tsconfig.app.json`
- `frontend/tsconfig.json`
- `frontend/tsconfig.node.json`
- `frontend/vite.config.ts`

## 21. feat: retain reusable procurement interface components

- `frontend/src/components/AgentFindings.tsx`
- `frontend/src/components/AgentProgress.tsx`
- `frontend/src/components/AgentReasoning.tsx`
- `frontend/src/components/NotificationBell.tsx`
- `frontend/src/components/SapIdCell.tsx`
- `frontend/src/components/ThreeWayMatch.tsx`
- `frontend/src/components/ui/Shell.tsx`
- `frontend/src/components/ui/alert.tsx`
- `frontend/src/components/ui/badge.tsx`
- `frontend/src/components/ui/button.tsx`
- `frontend/src/components/ui/card.tsx`
- `frontend/src/components/ui/collapsible.tsx`
- `frontend/src/components/ui/dialog.tsx`
- `frontend/src/components/ui/input.tsx`
- `frontend/src/components/ui/label.tsx`
- `frontend/src/components/ui/popover.tsx`
- `frontend/src/components/ui/spinner.tsx`
- `frontend/src/components/ui/table.tsx`
- `frontend/src/components/ui/tabs.tsx`

## 22. feat: connect the frontend through OIDC and durable job polling

- `frontend/src/AuthContext.tsx`
- `frontend/src/agentcore.ts`
- `frontend/src/api.ts`
- `frontend/src/auth.ts`
- `frontend/src/erpApi.ts`
- `frontend/src/hooks/useAgentStream.ts`
- `frontend/src/hooks/useSSE.ts`
- `frontend/src/runtimeConfig.ts`

## 23. feat: integrate procurement pages and invoice confirmation

- `frontend/src/pages/AgentChat.tsx`
- `frontend/src/pages/CommandCenter.tsx`
- `frontend/src/pages/Configuration.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/Decisions.tsx`
- `frontend/src/pages/EntryPortal.tsx`
- `frontend/src/pages/Errors.tsx`
- `frontend/src/pages/GoodsReceipts.tsx`
- `frontend/src/pages/Invoices.tsx`
- `frontend/src/pages/Payments.tsx`
- `frontend/src/pages/PurchaseOrders.tsx`
- `frontend/src/pages/Requisitions.tsx`
- `frontend/src/pages/Sourcing.tsx`
- `frontend/src/pages/TableViewer.tsx`

## 24. feat: prepare Netlify deployment and require authenticated sign-in

- `frontend/scripts/check-deploy-config.mjs`
- `frontend/src/App.tsx`
- `frontend/src/pages/Architecture.tsx`
- `frontend/src/pages/Login.tsx`
- `netlify.toml`

## 25. docs: document portable deployment validation and commit batches

- `.github/dependabot.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/dependabot-auto-merge.yml`
- `README.md`
- `docs/COMMIT_PLAN.md`
- `docs/MIGRATION.md`
- `docs/NETLIFY_DEPLOYMENT.md`

