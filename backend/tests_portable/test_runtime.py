import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock
import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import update
from services.auth import mint_internal_token, verify_token, current_claims
from services.database import engine, jobs as job_table
from runtime import jobs

def test_tokens_reject_forgery_expiry_and_wrong_audience(claims):
    from config import settings
    assert verify_token(mint_internal_token(claims))['email'] == claims['email']
    body = {'iss': 'aria-worker', 'sub': 'u', 'email': 'u@example.test', 'aud': 'aria-api',
            'exp': int(time.time()) + 60, 'realm_access': {'roles': ['procurement']}}
    for overrides, key in [({}, 'wrong-secret-' * 5), ({'exp': 1}, settings.service_secret),
                           ({'aud': 'other'}, settings.service_secret), ({'realm_access': {'roles': []}}, settings.service_secret)]:
        with pytest.raises(HTTPException) as exc:
            verify_token(jwt.encode({**body, **overrides}, key, algorithm='HS256'))
        assert exc.value.status_code == 401

def test_oidc_verifies_signature_issuer_and_audience(monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import rsa
    from services import auth
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(auth, '_jwks', lambda: SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=private.public_key())))
    body = {'iss': 'https://issuer.test/realms/aria', 'sub': 'u', 'email': 'u@example.test',
            'aud': 'aria-api', 'exp': int(time.time()) + 60, 'realm_access': {'roles': ['requester']}}
    assert verify_token(jwt.encode(body, private, algorithm='RS256'))['p2p_role'] == 'requester'
    with pytest.raises(HTTPException): verify_token(jwt.encode({**body, 'iss': 'https://evil.test'}, private, algorithm='RS256'))

def test_api_auth_and_cors(claims):
    from main import app
    with TestClient(app) as client:
        assert client.get('/api/health').status_code == 200
        assert client.get('/api/chat/sessions').status_code == 401
        requester = {**claims, 'p2p_role': 'requester'}
        response = client.post('/api/agents/workflow/runs', json={'document_id': 'MR-1'},
            headers={'Authorization': 'Bearer ' + mint_internal_token(requester), 'Origin': 'http://localhost:5173'})
        assert response.status_code == 403
        assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'

def test_queue_ownership_deduplication_and_recovery(claims):
    ident = jobs.enqueue('workflow', {'document_id': 'MR-1'}, claims, 'MR-1')
    with pytest.raises(HTTPException): jobs.enqueue('workflow', {}, claims, 'MR-1')
    assert jobs.claim()['id'] == ident
    assert jobs.claim() is None
    with pytest.raises(HTTPException): jobs.poll(ident, 0, {**claims, 'email': 'other@example.test'})
    jobs.append_event(ident, {'type': 'progress', 'step': 'Checked ERP'})
    assert jobs.poll(ident, 0, claims)['events'][0]['step'] == 'Checked ERP'
    with engine.begin() as conn: conn.execute(update(job_table).where(job_table.c.id == ident).values(heartbeat=time.time()-120))
    jobs.interrupt_stale()
    assert jobs.get_job(ident)['status'] == 'interrupted'
    with pytest.raises(HTTPException): jobs.enqueue('workflow', {}, claims, 'MR-1')
    jobs.set_status(ident, 'reconciled')
    assert jobs.enqueue('workflow', {}, claims, 'MR-1') != ident
    assert 'Bearer' not in jobs.get_job(ident)['payload']

async def test_progress_bridge_propagates_failure_without_hanging():
    from utils.progress_hooks import ProgressBridge
    def fail(prompt): raise RuntimeError('model unavailable')
    async def run():
        async for _ in ProgressBridge('test').run(fail, 'go'): pass
    with pytest.raises(RuntimeError, match='model unavailable'): await asyncio.wait_for(run(), 2)

def test_model_requires_explicit_non_aws_configuration(monkeypatch):
    from providers import build_model
    from config import settings
    monkeypatch.setattr(settings, 'llm_provider', 'groq')
    monkeypatch.setattr(settings, 'llm_api_key', '')
    with pytest.raises(ValueError, match='LLM_API_KEY'): build_model()
    monkeypatch.setattr(settings, 'llm_provider', 'bedrock')
    with pytest.raises(ValueError, match='Unsupported'): build_model()

def test_arithmetic_and_document_path_are_constrained():
    from runtime.tools import calculate
    from services.storage import save_document, read_document
    assert calculate('(3 + 5) * 2') == 16
    for expression in ['__import__("os").system("id")', '(1).__class__', '2 ** 100000', '1e309']:
        with pytest.raises(ValueError): calculate(expression)
    key = save_document(b'invoice')
    assert read_document(key) == b'invoice'
    with pytest.raises((ValueError, HTTPException)): read_document('../../.env')

def test_analysis_tool_cannot_write(claims):
    from runtime.tools import build_erp_tool
    token = current_claims.set(claims)
    try:
        with pytest.raises(PermissionError): build_erp_tool()('create_purchase_order', {})
    finally: current_claims.reset(token)

def test_sql_lifecycle_round_trip():
    from services.lifecycle import add_run_entry, get_lifecycle, set_status, Status
    add_run_entry('MR-1', 'analysis', agent='sourcing', summary='Checked suppliers')
    set_status('MR-1', Status.PENDING_APPROVAL, 'approval_gate')
    result = get_lifecycle('MR-1')
    assert result['status'] == 'PENDING_APPROVAL'
    assert result['runs'][0]['summary'] == 'Checked suppliers'

def test_po_requires_approval_and_blocks_duplicate_attempt(monkeypatch):
    from services import write_policy
    from adapters.models import PurchaseOrderCreate, RequisitionLineItem
    adapter = Mock()
    adapter.get_requisition.return_value = SimpleNamespace(line_items=[RequisitionLineItem(line_number=1,item_id='ITEM',quantity=2,unit_price=10)])
    body = PurchaseOrderCreate(supplier_id='S', line_items=[dict(line_number=1,item_id='ITEM',quantity=2,unit_price=10,line_amount=20,requisition_id='MR-1')])
    monkeypatch.setattr(write_policy, 'get_lifecycle', lambda _: {'status': 'PENDING_APPROVAL'})
    with pytest.raises(HTTPException): write_policy.create_po(adapter, body)
    adapter.create_purchase_order.assert_not_called()
    monkeypatch.setattr(write_policy, 'get_lifecycle', lambda _: {'status': 'APPROVED'})
    write_policy.record_approved_snapshot('MR-1', adapter.get_requisition.return_value, 'human')
    adapter.create_purchase_order.return_value = SimpleNamespace(order_id='PO-1')
    adapter.get_purchase_order.return_value = SimpleNamespace(order_id='PO-1', supplier_id='S',line_items=body.line_items)
    write_policy.create_po(adapter, body)
    with pytest.raises(HTTPException): write_policy.create_po(adapter, body.model_copy(update={'supplier_id': 'S2'}))
    assert adapter.create_purchase_order.call_count == 1

def test_nan_amounts_rejected():
    from adapters.models import PaymentCreate
    from pydantic import ValidationError
    with pytest.raises(ValidationError): PaymentCreate(supplier_id='S',amount=float('nan'),invoice_id='INV')

async def test_workflow_rejects_fabricated_order_id(monkeypatch, claims):
    import agentcore_app
    from adapters import canonical_api
    from adapters.models import Requisition
    outputs = iter([
        {'recommended_vendor': {'supplier_id': 'S', 'supplier_name': 'Supplier', 'score': 90}},
        {'recommendation': 'APPROVE', 'risk_level': 'LOW', 'total_amount': 1, 'confidence': 0.99, 'findings': []},
        {'action': 'CREATE', 'created_order_id': 'INVENTED-PO', 'total_amount': 20},
    ])
    def fake_agent(**kwargs):
        result = next(outputs)
        return lambda prompt: SimpleNamespace(message={'content': [{'text': json.dumps(result)}]})
    monkeypatch.setattr(agentcore_app, 'Agent', fake_agent)
    monkeypatch.setattr(agentcore_app, 'build_model', lambda: object())
    monkeypatch.setattr(agentcore_app, '_build_local_tools', lambda _: [])
    adapter = Mock()
    adapter.get_requisition.return_value = Requisition(requisition_id='MR-1', line_items=[dict(line_number=1,item_id='ITEM',quantity=2,unit_price=10)])
    monkeypatch.setattr(canonical_api, '_get_adapter', lambda caller: adapter)
    events = [json.loads(line) async for line in agentcore_app._run_workflow('MR-1', claims['email'])]
    assert events[-1]['result']['workflow_status'] == 'FAILED'
    assert 'verified' in events[-1]['result']['error'].lower()
    adapter.create_purchase_order.assert_not_called()

def test_changed_approved_requisition_cannot_be_ordered(monkeypatch):
    from services import write_policy
    from adapters.models import Requisition, PurchaseOrderCreate
    req = Requisition(requisition_id='MR-1', line_items=[dict(line_number=1,item_id='ITEM',quantity=2,unit_price=10)])
    write_policy.record_approved_snapshot('MR-1', req, 'approver')
    req.line_items[0].quantity = 3
    adapter = Mock()
    adapter.get_requisition.return_value = req
    monkeypatch.setattr(write_policy, 'get_lifecycle', lambda _: {'status': 'APPROVED'})
    body = PurchaseOrderCreate(supplier_id='S', line_items=[dict(line_number=1,item_id='ITEM',quantity=3,unit_price=10,line_amount=30,requisition_id='MR-1')])
    with pytest.raises(HTTPException): write_policy.create_po(adapter, body)
    adapter.create_purchase_order.assert_not_called()

def test_invoice_extraction_requires_confirmation(monkeypatch, claims):
    from api import invoices
    from services import dynamo, textract
    dynamo.put_item('invoice-jobs', {'job_id': 'JOB-1', 'owner': claims['email'], 'status': 'processing'})
    extracted = {'vendor_name': 'Supplier', 'invoice_number': 'INV-VENDOR', 'invoice_date': '2026-10-01',
        'due_date': '2026-10-31', 'po_number': 'PO-1', 'total_amount': '20',
        'line_items': [{'item_code': 'ITEM', 'quantity': 2, 'unit_price': 10, 'amount': 20}]}
    monkeypatch.setattr(textract, 'extract_invoice_from_bytes', lambda _: extracted)
    monkeypatch.setattr(invoices.erp_client, 'is_configured', lambda: True)
    response = Mock()
    response.json.return_value = {'order_id': 'PO-1', 'supplier_id': 'S'}
    request = Mock(return_value=response)
    monkeypatch.setattr(invoices.erp_client, 'request', request)
    invoices._process_invoice_job('JOB-1', b'invoice', claims['email'])
    job = dynamo.get_item('invoice-jobs', {'job_id': 'JOB-1'})
    assert job['status'] == 'needs_review'
    assert json.loads(job['proposal'])['line_items'][0]['item_id'] == 'ITEM'
    assert all(c.args[0] == 'GET' for c in request.call_args_list)

@pytest.mark.parametrize('result,expected', [({'value': 1}, 'completed'), ({'error': 'quota exhausted'}, 'failed')])
async def test_worker_runs_real_subprocess_and_persists_result(monkeypatch, claims, result, expected):
    from runtime import worker
    original_spawn = asyncio.create_subprocess_exec
    async def stub_spawn(*args, **kwargs):
        program = 'import sys,json; json.loads(sys.stdin.read()); print(' + repr(json.dumps({'type': 'result', 'result': result})) + ', flush=True)'
        return await original_spawn(args[0], '-c', program, **kwargs)
    monkeypatch.setattr(worker.asyncio, 'create_subprocess_exec', stub_spawn)
    ident = jobs.enqueue('workflow', {'document_id': 'MR-WORKER'}, claims, 'MR-WORKER')
    job = jobs.claim()
    await worker.execute(job)
    assert jobs.get_job(ident)['status'] == expected
    assert jobs.poll(ident, 0, claims)['events'][0]['result'] == result

async def test_worker_start_failure_retains_document_lock(monkeypatch, claims):
    from runtime import worker
    async def fail(*args, **kwargs): raise OSError('process unavailable')
    monkeypatch.setattr(worker.asyncio, 'create_subprocess_exec', fail)
    ident = jobs.enqueue('workflow', {}, claims, 'MR-START-FAIL')
    await worker.execute(jobs.claim())
    assert jobs.get_job(ident)['status'] == 'interrupted'
    with pytest.raises(HTTPException): jobs.enqueue('workflow', {}, claims, 'MR-START-FAIL')

def test_invoice_adapter_derives_order_from_erp_lines():
    from adapters.erpnext.adapter import ERPNextAdapter
    client = Mock()
    client.get.return_value = {'name': 'INV-1', 'supplier': 'S', 'status': 'Unpaid', 'outstanding_amount': 20,
        'items': [{'idx': 1, 'item_code': 'ITEM', 'qty': 2, 'rate': 10, 'amount': 20, 'purchase_order': 'PO-1'}]}
    invoice = ERPNextAdapter(client).get_invoice('INV-1')
    assert invoice.order_id == 'PO-1'
    assert invoice.line_items[0].order_id == 'PO-1'
