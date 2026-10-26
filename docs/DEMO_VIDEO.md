# Record the local procurement demonstration

Target length: 4–5 minutes. Show the running local application at `http://localhost:5173` and ERPNext at `http://localhost:8080`. Netlify serves the frontend/architecture preview; the backend in this recording runs on the laptop.

## Recording sequence

| Time | Screen | What to demonstrate |
| --- | --- | --- |
| 0:00–0:30 | Architecture | A company request moves through identity, persisted jobs, model-selected tools, human review and an independently verified ERP outcome. |
| 0:30–1:00 | Requisitions → `MAT-MR-2026-00001` | The actual request: 20 goggles and 10 gloves, total USD 370. The target is an ERP purchase order, with evidence. |
| 1:00–2:00 | Workflow/run history | Sourcing read two explicitly synthetic quotes. SafetyFirst quoted USD 370 / 7 days; MRO quoted USD 385 / 10 days. The agent chose a supplier and checked real items, duplicates and available budget evidence. |
| 2:00–2:45 | Decisions/history | Human review was required because the inputs are synthetic, the old requested date has passed, and this ERP persona could not read budget data. Explicit human approval accepted USD 370, Net 30 and November 2 delivery. That approval is recorded; do not claim an unrecorded on-screen button click. |
| 2:45–3:45 | Purchase Orders → ERPNext | Open the real order ID from the completed run. Compare supplier, item codes, quantities, rates, total, delivery date and Material Request links. The server reads the ERP record back before reporting completion. |
| 3:45–4:30 | Duplicate result and architecture | Show the duplicate check: HTTP 409 and one linked order before and after. Explain persisted state, bounded execution and reconciliation for uncertain writes. |
| 4:30–5:00 | README / validation | State the implemented scope and remaining limitations. Model scores are advisory; arithmetic and write checks are deterministic. The whole stack is not a free, always-online public deployment. |

## Before pressing record

- Keep Docker and the Vite terminal running. Refresh the frontend.
- Open the completed request, Decisions, Purchase Orders, ERP order and architecture in separate tabs.
- Hide email, unrelated tabs, `.env`, passwords, tokens and keys.
- Use the real completed run history. If showing recorded execution with waiting removed, label the edit.
- Keep synthetic quote labels visible. These are test supplier quotes, not real commercial commitments or historical performance.
- Check `docs/evidence/` and `docs/STATUS.md` for the exact verified outcome. A plan is not evidence that an operation succeeded.

## Evidence capture

After a verified purchase order exists:

```sh
docker compose exec -T api python /app/scripts/demo-evidence.py \
  --job ea7b447d-ff79-4b40-903b-3a1f171fc60a --check-duplicate --output /tmp/centralign-evidence.json
docker compose cp api:/tmp/centralign-evidence.json ./demo-evidence.local.json
```

The script reads an existing verified job identity, the actual ERP request/order, permanent write claim and persisted run history. Its duplicate probe must return 409 and leave exactly one linked order. No API key or bearer token is printed. Prefer the sanitized checked-in evidence summary for sharing; review local exports before publication.

## Submission checklist

1. Push the final tested commit and verify the repository opens.
2. Record and upload the video; verify the viewing permission from a private browser window.
3. Submit the repository URL and video URL. Describe the Netlify site as a frontend/architecture preview if its backend remains local.
4. Disclose the reused foundation accurately through the repository's source-origin and license notices.
5. Keep the laptop/backend available during any live interview, or use the recorded demonstration.

## After recording

`docker compose stop` stops the services and retains data. Stop Vite with Ctrl+C. Stopping does not reclaim Docker's image/volume storage. Back up records and private credentials before deleting volumes or resetting Docker Desktop; never run `down -v` as part of routine shutdown.
