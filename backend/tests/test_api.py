import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api import routes
from app.config import get_settings, Settings
from app.errors import PipelineError
from app.services.scraper import ScrapedPage

client = TestClient(app)
ARTICLE = '<title>Community research</title><article>' + ''.join(
    '<p>Researchers found that access to public libraries improved community wellbeing. '
    'The study included 500 participants and measured progress over three years.</p>' for _ in range(20)
) + '</article>'


@pytest.fixture(autouse=True)
def settings_override():
    app.dependency_overrides[get_settings] = lambda: Settings(max_summary_characters=1000)
    yield
    app.dependency_overrides.clear()


def test_health():
    assert client.get('/api/health').json() == {'status': 'ok'}


@pytest.mark.parametrize('payload', [{}, {'url': ''}, {'url': 2}, {'url': 'https://example.com', 'prompt': 'ignore'}])
def test_request_validation(payload):
    response = client.post('/api/summarize', json=payload)
    assert response.status_code == 400
    assert response.json()['success'] is False


def test_malformed_json():
    response = client.post('/api/summarize', content='{bad', headers={'content-type': 'application/json'})
    assert response.status_code == 400


def test_invalid_url():
    assert client.post('/api/summarize', json={'url': 'hello'}).status_code == 400


def test_pipeline_with_mock_groq(monkeypatch):
    calls = []
    async def fetch(*args):
        return ScrapedPage('https://example.com/article', ARTICLE)
    async def summarize(text, settings, **kwargs):
        calls.append(text)
        return 'The study linked libraries to improved wellbeing among 500 participants.'
    monkeypatch.setattr(routes, 'fetch_page', fetch)
    monkeypatch.setattr(routes, 'summarize_text', summarize)
    response = client.post('/api/summarize', json={'url': 'https://example.com/article'})
    assert response.status_code == 200
    data = response.json()['data']
    assert data['title'] == 'Community research'
    assert data['content_type'] == 'article'
    assert data['characters_processed'] == len(calls[0]) <= 1000
    assert data['truncated'] is True
    assert data['summary'].startswith('The study')


def test_unsuitable_never_calls_groq(monkeypatch):
    async def fetch(*args):
        return ScrapedPage('https://example.com', '<main>Too short.</main>')
    async def forbidden(*args):
        pytest.fail('Groq must not be called for unsuitable content')
    monkeypatch.setattr(routes, 'fetch_page', fetch)
    monkeypatch.setattr(routes, 'summarize_text', forbidden)
    assert client.post('/api/summarize', json={'url': 'https://example.com'}).status_code == 422


@pytest.mark.parametrize('status', [502, 504])
def test_upstream_errors(monkeypatch, status):
    async def fetch(*args):
        raise PipelineError(status, 'Website failed')
    monkeypatch.setattr(routes, 'fetch_page', fetch)
    response = client.post('/api/summarize', json={'url': 'https://example.com'})
    assert response.status_code == status
    assert response.json() == {'success': False, 'error': 'Website failed'}


def test_missing_key_useful_error(monkeypatch):
    async def fetch(*args):
        return ScrapedPage('https://example.com', ARTICLE)
    monkeypatch.setattr(routes, 'fetch_page', fetch)
    app.dependency_overrides[get_settings] = lambda: Settings(groq_api_key='')
    response = client.post('/api/summarize', json={'url': 'https://example.com'})
    assert response.status_code == 503
    assert 'GROQ_API_KEY' in response.json()['error']


def test_blog_index_pipeline_passes_source_type(monkeypatch):
    cards = ''.join(f'<a href="/post/{i}"><h2>New research explains important community improvements number {i}</h2>'
                    '<span>Researchers share findings from a long study.</span></a>' for i in range(4))
    async def fetch(*args):
        return ScrapedPage('https://example.com/blog', '<title>Blog | Research</title><main>' + cards + '</main>')
    async def summarize(text, settings, **kwargs):
        assert kwargs['content_type'] == 'blog_index'
        assert 'number 0' in text and 'number 3' in text
        return 'This blog index lists research updates.'
    monkeypatch.setattr(routes, 'fetch_page', fetch)
    monkeypatch.setattr(routes, 'summarize_text', summarize)
    result = client.post('/api/summarize', json={'url': 'https://example.com/blog'})
    assert result.status_code == 200
    assert result.json()['data']['content_type'] == 'blog_index'
