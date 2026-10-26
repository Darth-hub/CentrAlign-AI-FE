# Synthetic quote-backed demo request

These are explicitly fictional inputs for the local Apex Manufacturing Group prototype. They are not supplier commitments, historical transactions, or purchasing approval.

Target request: `MAT-MR-2026-00001`, containing 20 safety goggles (`MAT-SF-001`) and 10 boxes of gloves (`MAT-SF-002`).

| Fixture supplier | Goggles unit price | Gloves unit price | Total USD | Quoted delivery | Terms |
| --- | ---: | ---: | ---: | --- | --- |
| SafetyFirst Equipment Co | 11.50 | 14.00 | 370.00 | 7 days | Net 30 |
| MRO Warehouse Direct | 12.00 | 14.50 | 385.00 | 10 days | Net 30 |

Run only against the prepared demo tenant:

```sh
docker compose run --rm --no-deps bootstrap python /app/scripts/seed-demo-quotes.py --requisition MAT-MR-2026-00001 --allow-synthetic-demo
```

The command verifies the demo user, ERP requisition and active suppliers. It stores scoped quote records in the application database and creates no ERP orders. Quotes are valid for 30 days from initial seeding; reruns do not overwrite or silently renew them. The source label and quote IDs are returned to agents.

After any currently active sourcing run finishes, run the full workflow for the target request. Synthetic quote context requires human review even if the model recommends automatic approval. The approver must inspect prices and delivery dates; the legacy request has historical requested dates. The PO stage still requires an unchanged approved snapshot and independently checks the written ERP record.

Quote records are retained with the application database and its backups. No purchase or delivery history was fabricated to make the test pass.
