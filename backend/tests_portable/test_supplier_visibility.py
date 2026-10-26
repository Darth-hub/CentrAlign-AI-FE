from unittest.mock import Mock
from adapters.erpnext.adapter import ERPNextAdapter
from adapters.models import SupplierStatus

def test_active_suppliers_exclude_disabled_records():
    client = Mock()
    # Includes a disabled row even if a misbehaving transport ignores filters.
    client.get_list.return_value = [
        {'name':'usable','supplier_name':'Usable','disabled':0},
        {'name':'disabled','supplier_name':'Disabled','disabled':1},
    ]
    result = ERPNextAdapter(client).list_suppliers(status='active')
    assert [s.supplier_id for s in result.suppliers] == ['usable']
    assert ['disabled','=',0] in client.get_list.call_args.kwargs['filters']
    assert 'disabled' in client.get_list.call_args.kwargs['fields']

def test_supplier_detail_preserves_disabled_status():
    client = Mock()
    client.get.return_value = {'name':'disabled','supplier_name':'Disabled','disabled':1}
    assert ERPNextAdapter(client).get_supplier('disabled').status == SupplierStatus.INACTIVE
