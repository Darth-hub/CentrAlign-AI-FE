"""Deterministic checks at the ERP write boundary, independent of model claims."""
from decimal import Decimal
from datetime import date
import re
from fastapi import HTTPException
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from services.database import engine, records, encode
from services.lifecycle import get_lifecycle

def claim_write(key, evidence):
    # A permanent claim prevents replay after a lost response. Administrators
    # reconcile failed/unknown writes in ERP before explicitly releasing a claim.
    try:
        with engine.begin() as conn:
            conn.execute(insert(records).values(collection="write-claims", key=key, body=encode(evidence)))
    except IntegrityError as exc:
        raise HTTPException(409, "Write already attempted; reconcile the existing ERP record before retrying") from exc

def _fingerprint(requisition):
    import hashlib, json
    lines = sorted((str(li.item_id), float(li.quantity), None if li.unit_price is None else float(li.unit_price))
                   for li in requisition.line_items)
    return hashlib.sha256(json.dumps(lines, allow_nan=False).encode()).hexdigest()

def record_approved_snapshot(req_id, requisition, actor):
    from services.dynamo import put_item
    put_item("approval-snapshots", {"document_id": req_id, "fingerprint": _fingerprint(requisition), "actor": actor})


def _check_amount_permission(amount):
    from services.auth import current_claims
    if amount > 50000 and current_claims.get().get("p2p_role") != "admin":
        raise HTTPException(403, "Amounts above 50000 require the admin role")


def create_po(adapter, data):
    _check_amount_permission(sum(li.quantity * li.unit_price for li in data.line_items))
    if not data.line_items: raise HTTPException(422, "PO requires line items")
    req_ids = {li.requisition_id for li in data.line_items}
    if len(req_ids) != 1 or not next(iter(req_ids)):
        raise HTTPException(422, "PO lines must refer to one approved requisition")
    req_id = next(iter(req_ids))
    if (get_lifecycle(req_id) or {}).get("status") not in {"APPROVED", "PO_GENERATION"}:
        raise HTTPException(403, "Requisition must be approved before creating a PO")
    original = adapter.get_requisition(req_id)
    from services.dynamo import get_item
    snapshot = get_item("approval-snapshots", {"document_id": req_id})
    if not snapshot or snapshot["fingerprint"] != _fingerprint(original):
        raise HTTPException(409, "Requisition changed or has no approval snapshot; obtain fresh approval")
    original_lines = {line.item_id: line for line in original.line_items}
    if len(original_lines) != len(original.line_items) or {line.item_id for line in data.line_items} != set(original_lines):
        raise HTTPException(422, "This prototype requires one PO containing every approved item exactly once")
    seen = set()
    for line in data.line_items:
        if line.item_id in seen: raise HTTPException(422, "Duplicate PO line item")
        seen.add(line.item_id)
        source = original_lines.get(line.item_id)
        if not source or line.quantity <= 0 or line.quantity != source.quantity or line.unit_price < 0:
            raise HTTPException(422, "PO line differs from approved requisition")
        # Do not let generated prices exceed the approved requisition price.
        if source.unit_price is None or line.unit_price > source.unit_price:
            raise HTTPException(422, "PO price exceeds the approved requisition price")
    claim_write(f"po:{req_id}", {"requisition": req_id, "supplier": data.supplier_id})
    created = adapter.create_purchase_order(data)
    verified = adapter.get_purchase_order(created.order_id)
    if verified.supplier_id != data.supplier_id or not verified.line_items:
        raise HTTPException(502, "PO read-back did not match; reconcile ERP before retrying")
    expected = sorted((li.item_id, li.quantity, li.unit_price) for li in data.line_items)
    actual = sorted((li.item_id, li.quantity, li.unit_price) for li in verified.line_items)
    if expected != actual:
        raise HTTPException(502, "PO lines differ on read-back; reconcile ERP before retrying")
    from sqlalchemy import update
    with engine.begin() as conn:
        conn.execute(update(records).where(records.c.collection == "write-claims", records.c.key == f"po:{req_id}")
            .values(body=encode({"requisition": req_id, "supplier": data.supplier_id,
                "status": "verified", "order_id": verified.order_id})))
    return verified

def create_payment(adapter, data):
    _check_amount_permission(data.amount)
    if not data.invoice_id: raise HTTPException(422, "Payment must reference an invoice")
    inv = adapter.get_invoice(data.invoice_id)
    if inv.supplier_id != data.supplier_id or not inv.order_id:
        raise HTTPException(422, "Payment supplier/PO must match the invoice")
    if str(inv.status) not in {"submitted", "unpaid", "partially_paid", "overdue", "InvoiceStatus.SUBMITTED", "InvoiceStatus.UNPAID", "InvoiceStatus.PARTIALLY_PAID", "InvoiceStatus.OVERDUE"}:
        raise HTTPException(409, "Invoice must be submitted before payment")
    po = adapter.get_purchase_order(inv.order_id)
    receipts = adapter.list_receipts(order_id=inv.order_id)
    po_lines = {line.item_id: line for line in po.line_items}
    received = {}
    for receipt in receipts.receipts:
        if "return" in (receipt.status or "").lower():
            raise HTTPException(409, "Receipt returns require manual matching in this prototype")
        if (receipt.status or "").lower() not in {"completed", "to bill", "submitted"}:
            continue
        for line in receipt.line_items:
            received[line.item_id] = received.get(line.item_id, 0) + line.quantity_received
    billed = {}
    # Include other active invoices so repeated billing cannot consume the same receipt twice.
    for other in adapter.list_invoices(supplier_id=inv.supplier_id).invoices:
        if other.invoice_id == inv.invoice_id or other.order_id != inv.order_id:
            continue
        if str(getattr(other.status, "value", other.status)) in {"cancelled", "return"}:
            continue
        if not other.line_items:
            raise HTTPException(409, "Cannot verify quantities on another invoice for this PO")
        for line in other.line_items:
            billed[line.item_id] = billed.get(line.item_id, 0) + line.quantity
    seen = set()
    if not inv.line_items: raise HTTPException(422, "Invoice has no lines")
    for line in inv.line_items:
        if line.item_id in seen:
            raise HTTPException(409, "Duplicate invoice lines require manual matching")
        seen.add(line.item_id)
        if line.quantity + billed.get(line.item_id, 0) > received.get(line.item_id, 0):
            raise HTTPException(409, "Combined invoices exceed received quantities")
        order_line = po_lines.get(line.item_id)
        if not order_line or line.unit_price < 0 or line.quantity <= 0 or line.quantity > received.get(line.item_id, 0):
            raise HTTPException(409, "Invoice quantities are not supported by goods receipts")
        if line.quantity > order_line.quantity or line.unit_price > order_line.unit_price * 1.03:
            raise HTTPException(409, "Invoice does not pass three-way matching")
    outstanding = Decimal(str(inv.outstanding_amount or 0))
    if outstanding <= 0: raise HTTPException(409, "Invoice has no outstanding balance")
    expected = outstanding
    match = re.search(r"(\d+(?:\.\d+)?)/(\d+)", inv.payment_terms or "")
    if match and inv.invoice_date:
        days = (date.today() - date.fromisoformat(inv.invoice_date)).days
        if 0 <= days <= int(match[2]) and 0 < Decimal(match[1]) < 100:
            discounted = (outstanding * (1 - Decimal(match[1]) / 100)).quantize(Decimal("0.01"))
            if abs(Decimal(str(data.amount)) - discounted) <= Decimal("0.01"): expected = discounted
    if abs(Decimal(str(data.amount)) - expected) > Decimal("0.01"):
        raise HTTPException(422, "Payment amount does not match the ERP balance or eligible discount")
    # Adapter derives a balanced discount deduction from authoritative balance.
    data.deductions = None
    claim_write(f"payment:{data.invoice_id}", {"invoice": data.invoice_id, "amount": str(expected)})
    return adapter.create_payment(data)


def confirmed_po(adapter, req_id):
    """Completion evidence comes from the tool boundary and ERP, never generated text."""
    import json
    with engine.connect() as conn:
        body = conn.execute(select(records.c.body).where(records.c.collection == "write-claims",
            records.c.key == f"po:{req_id}")).scalar_one_or_none()
    evidence = json.loads(body) if body else {}
    if evidence.get("status") != "verified":
        raise HTTPException(409, "No verified ERP purchase order was created")
    po = adapter.get_purchase_order(evidence["order_id"])
    if str(getattr(po.status, "value", po.status)) in {"cancelled", "closed"}:
        raise HTTPException(409, "Purchase order is no longer active")
    return po
