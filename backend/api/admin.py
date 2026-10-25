"""Administrative status; destructive reset is intentionally not exposed."""
import logging
from fastapi import APIRouter, Request
from services import erp_client
from services.auth import get_user_email
router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/status")
def data_status(request: Request):
    """Quick count of ERP records via canonical adapter API."""
    if not erp_client.is_configured():
        return {"error": "ERP adapter transport not configured"}

    user_email = get_user_email(request)
    counts = {}
    for entity in ["suppliers", "items", "requisitions", "purchase-orders", "receipts", "invoices", "payments"]:
        try:
            resp = erp_client.request("GET", f"/{entity}", user_email=user_email, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            counts[entity] = data.get("total", len(data.get("items", [])))
        except Exception as e:
            logger.warning("Failed to fetch count for %s: %s", entity, e)
            counts[entity] = -1

    return counts
