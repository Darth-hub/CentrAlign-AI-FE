from fastapi import HTTPException

def authorize(method, path, role):
    if method in {"GET", "HEAD", "OPTIONS"}: return
    if role == "admin": return
    if path.startswith(("/api/chat/", "/api/agents/chat")): return
    if path.startswith("/api/agents/"):
        if role in {"procurement", "approver", "ap_clerk"}: return
    elif path.startswith("/api/decisions"):
        if role in {"procurement", "approver"}: return
    elif path.startswith("/api/invoices"):
        if role in {"procurement", "ap_clerk", "approver"}: return
    elif path.startswith("/api/erp/"):
        entity = path.removeprefix("/api/erp/").split("/")[0]
        allowed = {
            "requisitions": {"requester", "procurement", "approver"},
            "purchase-orders": {"procurement", "approver"},
            "receipts": {"procurement"}, "invoices": {"ap_clerk", "procurement", "approver"},
            "payments": {"ap_clerk", "approver"}, "attach": {"ap_clerk", "procurement"},
        }
        if role in allowed.get(entity, set()): return
    raise HTTPException(403, "This role cannot perform that action")
