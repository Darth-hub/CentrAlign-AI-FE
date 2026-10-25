# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Invoice extraction jobs, explicit human confirmation, and verified ERP creation."""

import json
import logging
import os
import time
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional

from services import erp_client
from services.auth import get_user_email

logger = logging.getLogger("p2p.api.invoices")

router = APIRouter()

INVOICE_JOBS_TABLE = "invoice-jobs"
from services.dynamo import get_table


def _update_job(job_id: str, updates: dict):
    table = get_table(INVOICE_JOBS_TABLE)
    updates["updated_at"] = int(time.time())
    table.update_item(
        Key={"job_id": job_id},
        UpdateExpression="SET " + ", ".join(f"#{k} = :{k}" for k in updates),
        ExpressionAttributeNames={f"#{k}": k for k in updates},
        ExpressionAttributeValues={f":{k}": v for k, v in updates.items()},
    )


@router.post("/upload")
async def upload_invoice(file: UploadFile = File(...)):
    """Extract invoice data from a PDF/image (preview only, does not create in ERP)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".tiff"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"File type {ext} not supported.")

    try:
        file_bytes = await file.read()
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")

        from services.textract import extract_invoice_from_bytes
        result = extract_invoice_from_bytes(file_bytes)
        return json.loads(json.dumps(result, default=str))

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Invoice extraction failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/analyzeAndCreateInvoice")
async def analyze_and_create_invoice(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload a vendor invoice PDF → start async job to extract and create in ERP.

    Returns a job_id immediately. Poll GET /invoices/jobs/{job_id} for status.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # The job runs as this user against ERPNext, so identity must come from the
    # verified JWT claims — a client-supplied header would let any caller pick
    # whose ERP credentials the background job uses.
    user_email = get_user_email(request)

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    job_id = str(uuid.uuid4())

    # Store initial job record
    table = get_table(INVOICE_JOBS_TABLE)
    table.put_item(Item={
        "job_id": job_id,
        "status": "processing",
        "step": "Extracting invoice with the configured model...",
        "filename": file.filename or "",
        "owner": user_email,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        "ttl": int(time.time()) + 86400,  # 24h TTL
    })

    from services.storage import save_document
    from runtime.jobs import enqueue
    key = save_document(file_bytes)
    enqueue("invoice_upload", {"invoice_job_id": job_id, "storage_key": key}, request.state.claims, "invoice-upload:" + job_id)
    return {"job_id": job_id, "status": "processing"}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str, request: Request):
    """Poll job status for async invoice processing."""
    table = get_table(INVOICE_JOBS_TABLE)
    item = table.get_item(Key={"job_id": job_id}).get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")

    if item.get("owner") != get_user_email(request) and request.state.claims["p2p_role"] != "admin":
        raise HTTPException(403, "Job belongs to another user")

    result = {
        "job_id": item["job_id"],
        "status": item.get("status", "unknown"),
        "step": item.get("step", ""),
    }

    if item.get("status") in {"completed", "needs_review"}:
        extraction = item.get("extraction", "{}")
        invoice = item.get("invoice", "{}")
        result["extraction"] = json.loads(extraction) if isinstance(extraction, str) else extraction
        result["invoice"] = json.loads(invoice) if isinstance(invoice, str) else invoice

    if item.get("status") == "failed":
        result["error"] = item.get("error", "Unknown error")

    return result


def _process_invoice_job(job_id: str, file_bytes: bytes, user_email: Optional[str]):
    """Extract and prepare an invoice proposal. ERP creation requires explicit confirmation."""
    if not erp_client.is_configured():
        _update_job(job_id, {"status": "failed", "error": "ERP adapter transport not configured"})
        return

    # Step 1: Extract with the configured provider
    _update_job(job_id, {"step": "Extracting invoice data with the configured model..."})
    from services.textract import extract_invoice_from_bytes
    extraction = extract_invoice_from_bytes(file_bytes)
    logger.info("Job %s: extraction complete — vendor=%s, po=%s, items=%d",
                job_id, extraction.get("vendor_name"), extraction.get("po_number"),
                len(extraction.get("line_items", [])))

    po_number = extraction.get("po_number", "")
    if not po_number:
        _update_job(job_id, {
            "status": "failed",
            "error": "No PO reference found in the invoice.",
            "extraction": json.dumps(extraction, default=str),
        })
        return

    _update_job(job_id, {
        "step": f"Looking up PO {po_number} in ERP...",
        "po_number": po_number,
        "extraction": json.dumps(extraction, default=str),
    })

    # Step 2: Fetch PO from ERP via the canonical ERP API
    try:
        resp = erp_client.request(
            "GET", f"/purchase-orders/{po_number}", user_email=user_email, timeout=15,
        )
        resp.raise_for_status()
        po = resp.json()
    except Exception as e:
        _update_job(job_id, {
            "status": "failed",
            "error": f"PO {po_number} not found in ERP: {e}",
        })
        return

    # Step 3: Build invoice from extracted line items
    _update_job(job_id, {"step": "Creating invoice in ERP..."})

    extracted_items = extraction.get("line_items", [])
    line_items = []
    for i, li in enumerate(extracted_items):
        line_items.append({
            "line_number": i + 1,
            "item_id": li.get("item_code", li.get("item_id", "")),
            "quantity": float(li.get("quantity", 0)),
            "unit_price": float(li.get("unit_price", 0)),
            "line_amount": float(li.get("amount", li.get("line_amount", 0))),
            "order_id": po.get("order_id", po_number),
        })

    if not line_items:
        _update_job(job_id, {"status": "failed", "error": "No invoice lines extracted; manual review required"})
        return

    invoice_payload = {
        "supplier_id": po.get("supplier_id", ""),
        "vendor_invoice_number": extraction.get("invoice_number", ""),
        "invoice_date": extraction.get("invoice_date", ""),
        "due_date": extraction.get("due_date", ""),
        "order_id": po.get("order_id", po_number),
        "line_items": line_items,
    }

    _update_job(job_id, {"status": "needs_review", "step": "Review the extracted values before creating an invoice",
        "proposal": json.dumps(invoice_payload), "extraction": json.dumps(extraction)})
    return


@router.post("/jobs/{job_id}/confirm")
def confirm_invoice(job_id: str, request: Request):
    item = get_table(INVOICE_JOBS_TABLE).get_item(Key={"job_id": job_id}).get("Item")
    if not item or item.get("owner") != get_user_email(request):
        raise HTTPException(404, "Invoice job not found")
    if item.get("status") != "needs_review":
        raise HTTPException(409, "Invoice is not awaiting review")
    from services.write_policy import claim_write
    claim_write("invoice-upload:" + job_id, {"actor": get_user_email(request)})
    invoice_payload = json.loads(item["proposal"])
    user_email = get_user_email(request)
    po_number = invoice_payload["order_id"]
    # Confirmation is an explicit human action; ambiguous responses are not retried.
    try:
        resp = erp_client.request(
            "POST", "/invoices", json_body=invoice_payload, user_email=user_email,
        )
        resp.raise_for_status()
        created = resp.json()
        invoice_id = created.get("invoice_id")
        if not invoice_id: raise ValueError("ERP returned no invoice identifier")
        verified = erp_client.request("GET", f"/invoices/{invoice_id}", user_email=user_email)
        verified.raise_for_status()
        created = verified.json()
        if created.get("supplier_id") != invoice_payload["supplier_id"] or created.get("order_id") != po_number:
            raise ValueError("Invoice read-back differs from the confirmed proposal")
    except Exception as e:
        _update_job(job_id, {
            "status": "failed",
            "error": "Invoice creation was not confirmed; reconcile ERP before retrying",
        })
        raise HTTPException(502, "Invoice creation was not confirmed; reconcile ERP before retrying") from e

    logger.info("Job %s: invoice created — %s for PO %s",
                job_id, created.get("invoice_id"), po_number)

    # Persist evidence after ERP read-back succeeds
    _update_job(job_id, {
        "status": "completed",
        "step": "Invoice created successfully",
        "invoice": json.dumps(created, default=str),
    })
    return created


# ── Schedule Payment ─────────────────────────────────────────────────────────


class PaymentDeductionRequest(BaseModel):
    account: str = "Write Off - AMG"
    cost_center: str = "Main - AMG"
    amount: float = 0.0

class SchedulePaymentRequest(BaseModel):
    invoice_id: str
    supplier_id: str
    amount: float
    order_id: str = ""
    mode_of_payment: str = "Wire Transfer"
    deductions: list[PaymentDeductionRequest] = []
    match_result: dict = {}
    payment_analysis: dict = {}


@router.post("/schedulePayment")
def schedule_payment(body: SchedulePaymentRequest, request: Request):
    """Create a payment entry in ERP and record as a workflow in runs[].

    Records a payment_workflow in the MR lifecycle with children:
    - invoice_matching analysis (from frontend)
    - payment analysis (from frontend)
    - decision: payment scheduled
    """
    if not erp_client.is_configured():
        raise HTTPException(status_code=500, detail="ERP adapter transport not configured")

    # Attribute the payment to the verified caller, not a client-supplied name.
    user_email = get_user_email(request)

    try:
        payload = {
            "supplier_id": body.supplier_id,
            "amount": body.amount,
            "mode_of_payment": body.mode_of_payment,
            "invoice_id": body.invoice_id,
        }
        if body.deductions:
            payload["deductions"] = [d.model_dump() for d in body.deductions]
        resp = erp_client.request("POST", "/payments", json_body=payload, user_email=user_email)
        if not resp.ok:
            logger.error("Payment creation failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(
                status_code=502, detail=f"ERP payment creation failed: {resp.text}"
            )
        result = resp.json()
        logger.info("Payment created: %s for invoice %s", result.get("payment_id"), body.invoice_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Payment scheduling error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    # Record payment workflow in MR lifecycle runs[]
    try:
        from services.lifecycle import add_run_entry, get_lifecycle_by_po

        # Find the MR lifecycle record via PO
        tracking_doc_id = body.invoice_id
        if body.order_id:
            mr_lc = get_lifecycle_by_po(body.order_id)
            if mr_lc:
                tracking_doc_id = mr_lc["document_id"]

        # Create workflow parent
        wf_id = add_run_entry(
            document_id=tracking_doc_id,
            entry_type="workflow",
            agent="payment_workflow",
            status="completed",
            summary=f"Payment scheduled for {body.invoice_id}: {result.get('payment_id', '')}",
        )

        # Child: invoice matching result
        if body.match_result:
            add_run_entry(
                document_id=tracking_doc_id,
                entry_type="analysis",
                agent="invoice_matching",
                parent_id=wf_id,
                status="completed",
                recommendation=str(body.match_result.get("match_result", "")),
                confidence=float(body.match_result.get("confidence", 0)),
                summary=str(body.match_result.get("reasoning", "")),
                result=body.match_result,
            )

        # Child: payment analysis result
        if body.payment_analysis:
            add_run_entry(
                document_id=tracking_doc_id,
                entry_type="analysis",
                agent="payment",
                parent_id=wf_id,
                status="completed",
                recommendation=str(body.payment_analysis.get("payment_recommendation", "")),
                confidence=float(body.payment_analysis.get("confidence", 0)),
                summary=str(body.payment_analysis.get("reasoning", "")),
                result=body.payment_analysis,
            )

        # Child: decision — payment scheduled
        add_run_entry(
            document_id=tracking_doc_id,
            entry_type="decision",
            agent="payment",
            parent_id=wf_id,
            action="PAYMENT_SCHEDULED",
            decided_by=user_email,
            status="completed",
            summary=f"Payment {result.get('payment_id', '')} created: ${body.amount} via {body.mode_of_payment}",
            result=result,
        )

        logger.info("Payment workflow recorded in runs[] for %s", tracking_doc_id)
    except Exception as e:
        logger.warning("Failed to record payment workflow: %s", e)

    return result
