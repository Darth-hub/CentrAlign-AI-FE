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
