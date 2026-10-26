"""Execute a human-approved quote without another speculative model call."""
from fastapi import HTTPException
from adapters.models import PurchaseOrderCreate
from adapters.canonical_api import _get_adapter,Caller
from services.auth import current_claims
from services.dynamo import get_item
from services.supplier_quotes import get_quote_context
from services.write_policy import create_po,confirmed_po

def execute_approved_quote(document_id):
    claims=current_claims.get()
    if not claims or claims.get('p2p_role') not in {'procurement','approver','admin'}:
        raise HTTPException(403,'Procurement permission required')
    snapshot=get_item('approval-snapshots',{'document_id':document_id}) or {}
    consent=snapshot.get('procurement')
    if not consent: raise HTTPException(409,'No human-approved supplier quote is available')
    context=get_quote_context(document_id)
    quote=next((q for q in context['quotes'] if q['quote_id']==consent['quote_id'] and q['supplier_id']==consent['supplier_id']),None)
    if quote is None: raise HTTPException(409,'Approved quote is no longer eligible; obtain fresh review')
    adapter=_get_adapter(Caller(email=claims['email'],allow_service_account=False))
    request=adapter.get_requisition(document_id)
    # The approval snapshot and write boundary validate all commercial fields.
    lines=[{'line_number':i,'item_id':li.item_id,'quantity':li.quantity,
        'unit_price':consent['unit_prices'][li.item_id], 'unit_of_measure':li.unit_of_measure,
        'line_amount':li.quantity*consent['unit_prices'][li.item_id],
        'requisition_id':document_id,'warehouse':li.warehouse}
        for i,li in enumerate(request.line_items,1)]
    body=PurchaseOrderCreate(supplier_id=consent['supplier_id'],payment_terms=consent['payment_terms'],
        delivery_date=consent['delivery_date'],line_items=lines)
    created=create_po(adapter,body)
    verified=confirmed_po(adapter,document_id)
    return {'error':None,'error_code':None,'action':'CREATE','created_order_id':verified.order_id,
        'created_order_ids':[verified.order_id],'confidence':1.0,
        'reasoning':'Executed the explicitly human-approved quote through the guarded ERP tool and independently read the order back.',
        'execution_mode':'deterministic-approved-quote','quote_id':quote['quote_id'],
        'po_draft':body.model_dump(mode='json'),'delivery_risks':[], 'validation_issues':[]}
