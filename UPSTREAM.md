# Upstream provenance

This project is derived from **ARIA — sample-multi-agent-procure-to-pay**, published by Amazon Web Services:

https://github.com/aws-samples/sample-multi-agent-procure-to-pay

The downloaded source includes the MIT No Attribution (MIT-0) license in `LICENSE`. Original copyright and license files have been preserved. ERPNext, Keycloak, the frontend packages and other dependencies retain their respective licenses; the upstream repository's MIT-0 license does not relicense those dependencies.

The domain agents, ERP canonical adapter, original React application and demo data originate upstream. The portable migration adds or changes the Netlify configuration, model providers, OIDC integration, SQL persistence, persistent job execution, deterministic ERP write controls, invoice review, Docker deployment and tests. See `docs/MIGRATION.md`.

The original README is preserved at `docs/upstream/README-AWS.md`. The original `infra/`, `local/`, AWS architecture assets and AWS-specific tests are historical reference. They are not used by the new root Compose / Netlify deployment.

If importing this source into a new repository, label the import as an upstream import and describe subsequent migration commits honestly. Commit count is not evidence of original authorship or a measured engineering history.
