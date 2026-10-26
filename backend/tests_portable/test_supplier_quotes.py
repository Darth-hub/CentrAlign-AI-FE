from datetime import date,timedelta
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from services.auth import current_claims
from services.dynamo import put_item
from services.supplier_quotes import get_quote_context,require_quote_review
from adapters.models import Requisition,RequisitionLineItem,Supplier

@pytest.fixture
def quote_setup(claims,monkeypatch):
    from adapters import canonical_api
    request=Requisition(requisition_id='MR-quote',line_items=[RequisitionLineItem(item_id='PPE',quantity=20,unit_price=11.5)])
    adapter=Mock()
    adapter.get_requisition.return_value=request
    adapter.get_supplier.return_value=Supplier(supplier_id='vendor',supplier_name='Vendor')
    monkeypatch.setattr(canonical_api,'_get_adapter',lambda caller:adapter)
    token=current_claims.set(claims)
    yield adapter
    current_claims.reset(token)

def quote(**overrides):
    return {'quote_id':'DEMO-Q','requisition_id':'MR-quote','supplier_id':'vendor',
        'source':'synthetic-demo','label':'SYNTHETIC DEMO INPUT','valid_from':date.today().isoformat(),
        'valid_until':(date.today()+timedelta(days=30)).isoformat(),'currency':'USD','payment_terms':'Net 30','delivery_days':7,
        'line_items':[{'item_id':'PPE','quantity':20,'unit_price':11.5,'unit_of_measure':'Nos'}],**overrides}

def test_quote_requires_execution_identity():
    token=current_claims.set({})
    try:
        with pytest.raises(PermissionError):get_quote_context('MR-quote')
    finally:current_claims.reset(token)

def test_valid_quote_is_scoped_labeled_and_requires_human(quote_setup):
    put_item('supplier-quotes',quote())
    context=get_quote_context('MR-quote')
    assert context['quotes'][0]['quoted_total']==230
    assert context['quotes'][0]['source']=='synthetic-demo'
    result=require_quote_review('MR-quote',{'auto_approved':True,'recommendation':'APPROVE'})
    assert result['auto_approved'] is False and result['recommendation']=='ESCALATE'
    # No quote can turn a rejection into approval.
    assert require_quote_review('MR-quote',{'recommendation':'REJECT'})['recommendation']=='REJECT'

@pytest.mark.parametrize('change',[
    {'valid_until':(date.today()-timedelta(days=1)).isoformat()},
    {'requisition_id':'OTHER'},
    {'currency':'EUR'},
    {'line_items':[{'item_id':'PPE','quantity':1,'unit_price':11.5,'unit_of_measure':'Nos'}]},
    {'line_items':[{'item_id':'OTHER','quantity':20,'unit_price':11.5,'unit_of_measure':'Nos'}]},
])
def test_ineligible_quotes_are_not_presented(quote_setup,change):
    put_item('supplier-quotes',quote(**change))
    assert get_quote_context('MR-quote')['quotes']==[]

def test_disabled_supplier_is_excluded(quote_setup):
    quote_setup.get_supplier.return_value=Supplier(supplier_id='vendor',supplier_name='Vendor',status='inactive')
    put_item('supplier-quotes',quote())
    assert get_quote_context('MR-quote')['quotes']==[]

def test_erp_visibility_is_checked_before_quotes(quote_setup,monkeypatch):
    from services import supplier_quotes
    quote_setup.get_requisition.side_effect=PermissionError('not permitted')
    scan=Mock()
    monkeypatch.setattr(supplier_quotes,'scan_table',scan)
    with pytest.raises(PermissionError):get_quote_context('MR-quote')
    scan.assert_not_called()

def test_quote_scores_are_verified_independently_of_model_arithmetic(quote_setup):
    from services.supplier_quotes import ground_sourcing_result
    put_item('supplier-quotes',quote())
    result=ground_sourcing_result('MR-quote',{'recommended_supplier':{'supplier_id':'vendor','score':99},
        'confidence':1,'estimated_savings_vs_avg':100,'quote_ids':['invented']})
    assert result['recommended_supplier']['score']==66
    assert result['supplier_evaluations'][0]['total_score']==66
    assert result['quote_ids']==['DEMO-Q'] and result['estimated_savings_vs_avg']==0
    assert result['confidence']==.7 and result['requires_human_approval'] is True

def test_unquoted_supplier_cannot_be_substituted_by_model(quote_setup):
    from services.supplier_quotes import ground_sourcing_result
    put_item('supplier-quotes',quote())
    with pytest.raises(ValueError,match='no eligible quote'):
        ground_sourcing_result('MR-quote',{'recommended_supplier':{'supplier_id':'invented'}})

def test_approved_execution_requires_current_quote_before_write(quote_setup,monkeypatch):
    from services import approved_purchase
    from services.write_policy import record_approved_snapshot
    put_item('supplier-quotes',quote(valid_until=(date.today()-timedelta(days=1)).isoformat()))
    record_approved_snapshot('MR-quote',quote_setup.get_requisition.return_value,'buyer@example.test',
        {'supplier_id':'vendor','quote_id':'DEMO-Q','payment_terms':'Net 30',
         'delivery_date':(date.today()+timedelta(days=7)).isoformat(),'unit_prices':{'PPE':11.5}})
    create=Mock();monkeypatch.setattr(approved_purchase,'create_po',create)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:approved_purchase.execute_approved_quote('MR-quote')
    assert exc.value.status_code==409
    create.assert_not_called()

def test_approved_executor_cannot_run_as_requester(quote_setup):
    from services.approved_purchase import execute_approved_quote
    from fastapi import HTTPException
    token=current_claims.set({'email':'buyer@example.test','p2p_role':'requester'})
    try:
        with pytest.raises(HTTPException) as exc:execute_approved_quote('MR-quote')
        assert exc.value.status_code==403
    finally:current_claims.reset(token)
