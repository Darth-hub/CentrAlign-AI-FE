"""Durable execution endpoints. Polling survives Netlify/proxy request timeouts."""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from runtime import jobs
from services.auth import require_roles
from services.rate_limiter import check_agent_rate_limit
router = APIRouter()
AGENTS = {"workflow", "requisition", "sourcing", "po_management", "receiving", "invoice_matching", "payment"}
class RunInput(BaseModel):
    document_id: str = Field(min_length=1, max_length=200)
    order_id: str = ""
    resume_from: str = ""
@router.post("/{agent}/runs", status_code=202)
def start(agent: str, body: RunInput, request: Request):
    if agent not in AGENTS: raise HTTPException(404, "Unknown agent")
    claims = require_roles(request, "admin", "procurement", "approver", "ap_clerk")
    if agent in {"workflow", "po_management"} and claims["p2p_role"] == "ap_clerk":
        raise HTTPException(403, "Procurement permission required")
    if agent in {"workflow", "po_management"}:
        from services.lifecycle import get_lifecycle
        lifecycle = get_lifecycle(body.document_id) or {}
        if lifecycle.get("status") == "PO_CREATED":
            raise HTTPException(409, "This requisition already has a verified purchase order: " + str(lifecycle.get("po_order_id", "")))
    check_agent_rate_limit(claims["sub"])
    return {"job_id": jobs.enqueue(agent, body.model_dump(), claims, body.document_id), "status": "queued"}
@router.get("/runs/{job_id}/events")
def events(job_id: str, request: Request, after: int = 0):
    return jobs.poll(job_id, max(0, after), request.state.claims)
class ReconcileInput(BaseModel):
    evidence: str = Field(min_length=20, max_length=2000)
@router.post("/runs/{job_id}/reconcile")
def reconcile(job_id: str, body: ReconcileInput, request: Request):
    claims = require_roles(request, "admin")
    job = jobs.get_job(job_id, claims)
    if job["status"] != "interrupted": raise HTTPException(409, "Only interrupted jobs need reconciliation")
    jobs.append_event(job_id, {"type": "progress", "step": "ERP state reconciled by administrator",
        "actor": claims["email"], "evidence": body.evidence})
    jobs.set_status(job_id, "reconciled")
    return {"status": "reconciled"}
