"""Typed ERP operations bound to verified identity, with a write boundary."""
import ast
import json
import operator
from strands import tool
from services.auth import current_claims
from services.lifecycle import get_lifecycle
from config import settings

READS = {"list_suppliers", "get_supplier", "list_items", "get_item", "list_requisitions", "get_requisition",
         "list_purchase_orders", "get_purchase_order", "list_receipts", "get_receipt", "list_invoices",
         "get_invoice", "list_payments", "get_spend_summary", "get_supplier_performance", "get_budget_status",
         "list_cost_centers", "list_payment_terms"}

def build_erp_tool(stage="analysis"):
    calls = 0
    @tool
    def erp_operation(operation: str, parameters: dict) -> str:
        """Read ERP data or create an approved purchase order.

        Operations: list_suppliers(status,group), get_supplier(supplier_id), list_items(group,search),
        get_item(item_id), list_requisitions(status,requester), get_requisition(requisition_id),
        list_purchase_orders(supplier_id,status), get_purchase_order(order_id), list_receipts(order_id),
        get_receipt(receipt_id), list_invoices(supplier_id,status), get_invoice(invoice_id), list_payments(),
        get_spend_summary(), get_supplier_performance(), get_budget_status(cost_center), list_cost_centers(),
        list_payment_terms(). create_purchase_order takes supplier_id, payment_terms, delivery_date,
        line_items [{line_number,item_id,quantity,unit_price,line_amount,requisition_id}]. It is available ONLY during
        the PO stage for a server-approved requisition. Identity is set by the server, never in parameters.

        Args:
            operation: Exact operation name from this list.
            parameters: Object with the arguments for the selected operation. Empty object for no arguments.
        """
        nonlocal calls
        calls += 1
        if calls > settings.max_tool_calls: raise RuntimeError("Tool-call budget exhausted")
        claims = current_claims.get()
        if not claims: raise PermissionError("Missing execution identity")
        parameters = {k: v for k, v in parameters.items() if k != "user_email"}
        if operation not in READS:
            if operation != "create_purchase_order" or stage != "po_management":
                raise PermissionError("This agent stage is read-only")
            if claims["p2p_role"] not in {"admin", "procurement", "approver"}:
                raise PermissionError("Not permitted to create purchase orders")
            lines = parameters.get("line_items", [])
            if not lines or any(not line.get("requisition_id") for line in lines):
                raise PermissionError("Every PO line must reference an approved requisition")
            for req_id in {line["requisition_id"] for line in lines}:
                lifecycle = get_lifecycle(req_id) or {}
                if lifecycle.get("status") not in {"APPROVED", "PO_GENERATION"}:
                    raise PermissionError("Requisition is not approved")
        from adapters.canonical_api import _get_adapter, _dispatch_tool, Caller
        adapter = _get_adapter(Caller(email=claims["email"], allow_service_account=False))
        result = _dispatch_tool(operation, parameters, adapter)
        return json.dumps(result.model_dump(mode="json", exclude_none=True) if hasattr(result, "model_dump") else result, default=str, separators=(",", ":"))
    return erp_operation

@tool
def calculate(expression: str) -> float:
    """Evaluate arithmetic (+, -, *, / and parentheses). No Python execution or file/network access.

    Args:
        expression: Arithmetic using numeric literals only, at most 500 characters.
    """
    if len(expression) > 500: raise ValueError("Expression too long")
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
    def visit(node, depth=0):
        if depth > 30: raise ValueError("Expression too deep")
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}: value = float(node.value)
        elif isinstance(node, ast.BinOp) and type(node.op) in operations:
            value = operations[type(node.op)](visit(node.left, depth+1), visit(node.right, depth+1))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = visit(node.operand, depth+1) * (-1 if isinstance(node.op, ast.USub) else 1)
        else: raise ValueError("Only arithmetic is allowed")
        import math
        if not math.isfinite(value) or abs(value) > 1e18: raise ValueError("Numeric result outside limits")
        return value
    return visit(ast.parse(expression, mode="eval").body)


@tool
def supplier_quotes(requisition_id: str) -> str:
    """Read current supplier quotations and the ERP-verified request in one call.

    Includes supplier identities/status, exact item quantities, unit prices,
    currency, validity, payment terms and quoted delivery days. Sources are
    explicitly labeled; these are not historical performance or approval.

    Args:
        requisition_id: The purchase requisition to obtain quote evidence for.
    """
    from services.supplier_quotes import get_quote_context
    return json.dumps(get_quote_context(requisition_id), default=str, separators=(',', ':'))
