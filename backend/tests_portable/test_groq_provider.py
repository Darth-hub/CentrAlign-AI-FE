import json
from types import SimpleNamespace
import httpx
import openai
import pytest
from strands.models.openai import OpenAIModel
from providers.groq import GroqModel, ToolCallFormatError

async def collect(model):
    return [event async for event in model.stream([{'role':'user','content':[{'text':'test'}]}])]

async def test_rejects_partial_response_and_retries_without_releasing_tools(monkeypatch):
    calls = []
    async def fake_stream(self, *args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            yield {'partial': True}
            raise openai.APIError('bad tool call', request=httpx.Request('POST','https://example.test'), body={'code':'tool_use_failed'})
        yield {'valid': True}
    monkeypatch.setattr(OpenAIModel, 'stream', fake_stream)
    assert await collect(GroqModel(model_id='test')) == [{'valid': True}]
    assert len(calls) == 2

async def test_invalid_tool_response_has_a_bounded_retry(monkeypatch):
    calls = []
    async def fake_stream(self, *args, **kwargs):
        calls.append(1)
        raise ToolCallFormatError('malformed')
        yield
    monkeypatch.setattr(OpenAIModel, 'stream', fake_stream)
    with pytest.raises(ToolCallFormatError, match='twice'):
        await collect(GroqModel(model_id='test'))
    assert len(calls) == 2

async def test_unrelated_api_error_is_not_retried(monkeypatch):
    calls = []
    async def fake_stream(self, *args, **kwargs):
        calls.append(1)
        raise openai.APIError('other failure', request=httpx.Request('POST','https://example.test'), body={'code':'other'})
        yield
    monkeypatch.setattr(OpenAIModel, 'stream', fake_stream)
    with pytest.raises(openai.APIError): await collect(GroqModel(model_id='test'))
    assert len(calls) == 1

@pytest.mark.parametrize('arguments', ['{broken', '[]', '"import os"'])
def test_tool_arguments_must_be_json_objects(arguments):
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[SimpleNamespace(function=SimpleNamespace(arguments=arguments))]))])
    with pytest.raises(ToolCallFormatError): GroqModel(model_id='test')._format_non_streaming_response(response)

def test_groq_factory_selects_complete_serial_tool_responses(monkeypatch):
    from config import settings
    from providers import build_model
    monkeypatch.setattr(settings,'llm_provider','groq')
    monkeypatch.setattr(settings,'llm_model','openai/gpt-oss-120b')
    monkeypatch.setattr(settings,'llm_api_key','synthetic-test-key')
    model = build_model()
    assert model.config['stream'] is False
    assert model.config['params']['parallel_tool_calls'] is False
    assert model.config['params']['reasoning_effort'] == 'low'

def test_prompt_json_example_is_valid():
    from agents.sourcing_agent import _build_system_prompt
    from agents.invoice_matching_agent import _build_system_prompt as invoice_prompt
    for prompt in [_build_system_prompt(), invoice_prompt()]:
        assert '{{' not in prompt
    prompt = _build_system_prompt()
    example = prompt.split('no explanation outside JSON):',1)[1].split('**split_award format**',1)[0].strip()
    assert isinstance(json.loads(example),dict)


def test_compact_erp_result_preserves_zero_and_false(claims, monkeypatch):
    from pydantic import BaseModel
    from services.auth import current_claims
    from runtime.tools import build_erp_tool
    from adapters import canonical_api
    class Result(BaseModel):
        quantity: int = 0
        blocked: bool = False
        unknown: str | None = None
    monkeypatch.setattr(canonical_api, '_get_adapter', lambda caller: object())
    monkeypatch.setattr(canonical_api, '_dispatch_tool', lambda *args: Result())
    token = current_claims.set(claims)
    try:
        value = json.loads(build_erp_tool()('get_requisition', {'requisition_id': 'MR-test'}))
        assert value == {'quantity': 0, 'blocked': False}
    finally:
        current_claims.reset(token)
