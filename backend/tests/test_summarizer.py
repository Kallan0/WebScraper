import httpx
import pytest
from app.config import Settings
from app.errors import PipelineError
from app.services import summarizer


@pytest.mark.parametrize('response', [httpx.Response(401), httpx.Response(429),
    httpx.Response(200, json={}), httpx.Response(200, json={'choices': []}),
    httpx.Response(200, json={'choices': [{'message': {'content': ''}}]})])
async def test_provider_failures_are_safe(monkeypatch, response):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(summarizer.httpx, 'AsyncClient', lambda **kwargs: real_client(
        transport=httpx.MockTransport(lambda request: response)))
    with pytest.raises(PipelineError) as error:
        await summarizer.summarize_text('Some content', Settings(groq_api_key='test-secret'))
    assert error.value.status_code == 502
    assert 'test-secret' not in error.value.message


async def test_provider_payload(monkeypatch):
    import json
    real_client = httpx.AsyncClient
    def handler(request):
        payload = json.loads(request.content)
        assert request.headers['authorization'] == 'Bearer test-secret'
        assert payload['reasoning_effort'] == 'low'
        assert payload['max_completion_tokens'] == 1024
        assert payload['messages'][0]['role'] == 'system'
        assert 'untrusted' in payload['messages'][0]['content']
        assert payload['messages'][1]['content'].endswith('Some content')
        return httpx.Response(200, json={'choices': [{'message': {'content': '  Useful summary.  '}}]})
    monkeypatch.setattr(summarizer.httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler)))
    assert await summarizer.summarize_text('Some content', Settings(groq_api_key='test-secret', groq_model='openai/gpt-oss-20b')) == 'Useful summary.'


async def test_index_prompt_does_not_claim_full_articles(monkeypatch):
    import json
    real_client = httpx.AsyncClient
    def handler(request):
        payload = json.loads(request.content)
        prompt = payload['messages'][0]['content']
        assert 'not full articles' in prompt
        assert 'Do not imply that you have read the linked articles' in prompt
        return httpx.Response(200, json={'choices': [{'message': {'content': 'The index lists research news.'}}]})
    monkeypatch.setattr(summarizer.httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler)))
    await summarizer.summarize_text('Research headlines', Settings(groq_api_key='test-secret'), content_type='blog_index')
