"""A process per job isolates agent globals and enforces a killable deadline."""
import asyncio
import json
import os
import sys
from services.auth import current_claims

async def main():
    envelope = json.loads(sys.stdin.read())
    claims = envelope["identity"]
    current_claims.set(claims)
    payload = envelope["input"]
    payload["user_email"] = claims["email"]
    if os.environ["AGENT_NAME"] == "invoice_upload":
        from api.invoices import _process_invoice_job
        from services.storage import read_document
        job_id = payload["invoice_job_id"]
        try:
            await asyncio.to_thread(_process_invoice_job, job_id, read_document(payload["storage_key"]), claims["email"])
        except Exception:
            from api.invoices import _update_job
            _update_job(job_id, {"status": "failed", "error": "Invoice extraction failed; check model availability and document readability"})
        from services.dynamo import get_item
        result = get_item("invoice-jobs", {"job_id": job_id})
        print(json.dumps({"type": "result", "result": result}), flush=True)
        return
    import agentcore_app
    async for event in agentcore_app.invoke(payload):
        print(event.strip(), flush=True)

if __name__ == "__main__": asyncio.run(main())
