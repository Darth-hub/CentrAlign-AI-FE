"""Quote evidence scoped to an ERP requisition; never purchase authorization."""
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from services.auth import current_claims
from services.dynamo import scan_table

class QuoteLine(BaseModel):
    model_config = ConfigDict(extra='forbid')
    item_id: str
    quantity: float = Field(gt=0, allow_inf_nan=False)
    unit_price: float = Field(gt=0, allow_inf_nan=False)
    unit_of_measure: str = 'Nos'

class SupplierQuote(BaseModel):
    model_config = ConfigDict(extra='forbid')
    quote_id: str
    requisition_id: str
    supplier_id: str
    source: Literal['synthetic-demo', 'supplier-provided']
    label: str
    valid_from: date
    valid_until: date
    currency: str = 'USD'
    payment_terms: str
    delivery_days: int = Field(gt=0, le=365)
    line_items: list[QuoteLine] = Field(min_length=1, max_length=100)

def get_quote_context(requisition_id):
    claims = current_claims.get()
    if not claims or not claims.get('email'):
        raise PermissionError('Verified execution identity required')
    from adapters.canonical_api import _get_adapter, Caller
    adapter = _get_adapter(Caller(email=claims['email'], allow_service_account=False))
    # Check ERP visibility before reading any quote records.
    requisition = adapter.get_requisition(requisition_id)
    needed = {line.item_id: line for line in requisition.line_items}
    result = []
    for record in scan_table('supplier-quotes'):
        if record.get('requisition_id') != requisition_id:
            continue
        quote = SupplierQuote.model_validate(record)
        if not quote.valid_from <= date.today() <= quote.valid_until or quote.currency != requisition.currency:
            continue
        lines = {line.item_id: line for line in quote.line_items}
        if len(lines) != len(quote.line_items) or set(lines) != set(needed):
            continue
        if any(lines[item].quantity < req.quantity or lines[item].unit_of_measure != req.unit_of_measure for item, req in needed.items()):
            continue
        supplier = adapter.get_supplier(quote.supplier_id)
        if supplier.status != 'active':
            continue
        total = sum(Decimal(str(needed[item].quantity)) * Decimal(str(line.unit_price)) for item, line in lines.items())
        result.append({**quote.model_dump(mode='json'), 'quoted_total': float(total),
            'verified_supplier': {'supplier_id': supplier.supplier_id, 'supplier_name': supplier.supplier_name, 'status': supplier.status}})
    return {'requisition': requisition.model_dump(mode='json', exclude_none=True),
        'quotes': result, 'requires_human_approval': any(q['source'] == 'synthetic-demo' for q in result),
        'notice': 'Quote evidence is not a historical purchase or delivery-performance record. Synthetic demo quotes require human approval.'}

def require_quote_review(requisition_id, analysis):
    if get_quote_context(requisition_id)['requires_human_approval']:
        analysis['auto_approved'] = False
        if analysis.get('recommendation') != 'REJECT':
            analysis['recommendation'] = 'ESCALATE'
        if not isinstance(analysis.get('findings'), list):
            analysis['findings'] = []
        analysis['findings'].append({'check': 'Synthetic quote evidence', 'status': 'REVIEW',
            'detail': 'Supplier quotes are synthetic demo inputs. A human must review supplier, prices and delivery date.'})
    return analysis
