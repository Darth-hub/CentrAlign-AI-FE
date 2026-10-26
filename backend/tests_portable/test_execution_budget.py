import asyncio
import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

async def test_all_tool_types_share_budget(monkeypatch):
    from config import settings
    from utils.progress_hooks import _ToolProgressHook
    monkeypatch.setattr(settings, 'max_tool_calls', 2)
    queue=asyncio.Queue()
    hook=_ToolProgressHook(queue,asyncio.get_running_loop(),'sourcing')
    events=[SimpleNamespace(tool_use={'name':name,'input':{}},cancel_tool=False)
            for name in ['supplier_quotes','calculate','erp_operation']]
    for event in events:hook._on_before_tool(event)
    await asyncio.sleep(0)
    assert queue.qsize()==2
    assert events[0].cancel_tool is False and events[1].cancel_tool is False
    assert 'budget exhausted' in events[2].cancel_tool

async def test_turn_limit_never_becomes_completed_answer():
    from utils.progress_hooks import ProgressBridge
    agent=Mock()
    agent.event_loop_metrics=object()
    agent.return_value=SimpleNamespace(stop_reason='max_turns')
    with pytest.raises(RuntimeError,match='execution budget'):
        async for _ in ProgressBridge('sourcing').run(agent,'evaluate'): pass
    assert agent.call_args.kwargs['limits']['turns'] > 0

def test_qwen_uses_bounded_instruct_mode(monkeypatch):
    from config import settings
    import providers.groq
    from providers import build_model
    monkeypatch.setattr(settings,'llm_provider','groq')
    monkeypatch.setattr(settings,'llm_model','qwen/qwen3.8-27b')
    monkeypatch.setattr(settings,'llm_api_key','test-placeholder')
    factory=Mock()
    monkeypatch.setattr(providers.groq,'GroqModel',factory)
    build_model()
    assert factory.call_args.kwargs['params']['reasoning_effort']=='none'

def test_completed_request_rejected_before_new_job(claims):
    from main import app
    from fastapi.testclient import TestClient
    from services.auth import mint_internal_token
    from services.lifecycle import record_po_created
    from sqlalchemy import select,func
    from services.database import engine,jobs
    record_po_created('MR-done','PO-verified',total_amount=370)
    with TestClient(app) as client:
        response=client.post('/api/agents/workflow/runs',json={'document_id':'MR-done'},
            headers={'Authorization':'Bearer '+mint_internal_token(claims)})
    assert response.status_code==409
    assert 'PO-verified' in response.json()['detail']
    with engine.connect() as conn: assert conn.execute(select(func.count()).select_from(jobs)).scalar()==0
