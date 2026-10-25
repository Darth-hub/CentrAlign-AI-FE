# Source origin and licensing

This repository includes code from [sample-multi-agent-procure-to-pay](https://github.com/aws-samples/sample-multi-agent-procure-to-pay), published by Amazon Web Services under the MIT No Attribution (MIT-0) license. Its original license is retained in `LICENSE`.

The procurement agent definitions, canonical ERP adapter, React application structure and example data include source from that project. This repository also contains its own application configuration, model-provider integration, OIDC wiring, SQL job runtime, deterministic write controls, invoice review, deployment configuration and validation work.

ERPNext, Keycloak, the agent SDK and other dependencies retain their respective licenses. See `THIRD-PARTY-LICENSES.md`.

Historical documentation is retained under `docs/upstream/`. The current architecture and implementation are documented in `docs/ARCHITECTURE.md` and `docs/IMPLEMENTATION.md`.
