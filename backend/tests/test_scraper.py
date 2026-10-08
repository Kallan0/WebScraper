import socket
import httpx
import pytest
from app.config import Settings
from app.errors import PipelineError
from app.utils.validators import normalize_url, validate_destination, Destination
from app.services import scraper


@pytest.mark.parametrize('url', ['hello', 'file:///etc/passwd', 'ftp://example.com',
                                  'https://user:pass@example.com', 'https://example.com:8080',
                                  'https://example.com/\\localhost', 'https://example.com/ bad'])
def test_invalid_url(url):
    with pytest.raises(PipelineError) as error:
        normalize_url(url)
    assert error.value.status_code == 400


@pytest.mark.parametrize('url', ['http://127.0.0.1', 'http://10.0.0.1', 'http://192.168.1.1',
                                  'http://172.16.0.1', 'http://0.0.0.0', 'http://[::1]',
                                  'http://[::ffff:8.8.8.8]', 'http://169.254.169.254',
                                  'http://localhost', 'http://app.local'])
async def test_private_destinations(url):
    with pytest.raises(PipelineError) as error:
        await validate_destination(url)
    assert error.value.status_code == 400


async def test_mixed_dns_is_rejected(monkeypatch):
    async def resolve(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]
    monkeypatch.setattr('asyncio.get_running_loop', lambda: type('Loop', (), {'getaddrinfo': staticmethod(resolve)})())
    with pytest.raises(PipelineError):
        await validate_destination('https://example.com')


async def public_destination(url):
    normalized = normalize_url(url)
    if 'localhost' in normalized:
        raise PipelineError(400, 'Private destination')
    return Destination(normalized, 'example.com', 443, ('93.184.216.34',))


async def fetch_mock(handler, monkeypatch, **settings):
    monkeypatch.setattr(scraper, 'validate_destination', public_destination)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await scraper._fetch(client, 'https://example.com/article', Settings(**settings))


async def test_fetch_pins_ip_preserving_host_and_tls(monkeypatch):
    def handler(request):
        assert request.url.host == '93.184.216.34'
        assert request.headers['Host'] == 'example.com'
        assert request.extensions['sni_hostname'] == 'example.com'
        return httpx.Response(200, headers={'content-type': 'text/html'}, text='<p>Hello world</p>')
    page = await fetch_mock(handler, monkeypatch)
    assert page.html == '<p>Hello world</p>'
    assert page.url == 'https://example.com/article'


@pytest.mark.parametrize(('response', 'status'), [
    (httpx.Response(404), 502),
    (httpx.Response(200, headers={'content-type': 'application/pdf'}), 422),
    (httpx.Response(200, headers={'content-type': 'text/html'}, content=b'A' * 101), 422),
    (httpx.Response(200, headers={'content-type': 'text/html', 'content-length': '101'}), 422),
    (httpx.Response(302, headers={'location': 'http://localhost/secret'}), 400),
    (httpx.Response(302, headers={'location': '/loop'}), 502),
])
async def test_fetch_failures(response, status, monkeypatch):
    with pytest.raises(PipelineError) as error:
        await fetch_mock(lambda request: response, monkeypatch, max_response_bytes=100, max_redirects=1)
    assert error.value.status_code == status


async def test_redirect_revalidated(monkeypatch):
    urls = []
    async def validator(url):
        urls.append(url)
        return await public_destination(url)
    monkeypatch.setattr(scraper, 'validate_destination', validator)
    responses = iter([httpx.Response(302, headers={'location': '/final'}),
                      httpx.Response(200, headers={'content-type': 'text/html'}, text='Final page')])
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: next(responses))) as client:
        result = await scraper._fetch(client, 'https://example.com/start', Settings())
    assert urls == ['https://example.com/start', 'https://example.com/final']
    assert result.url.endswith('/final')


async def test_timeout_mapped(monkeypatch):
    async def timeout(*args):
        raise httpx.ReadTimeout('slow')
    monkeypatch.setattr(scraper, '_fetch', timeout)
    with pytest.raises(PipelineError) as error:
        await scraper.fetch_page('https://example.com', Settings())
    assert error.value.status_code == 504


@pytest.mark.parametrize('address', ['224.0.0.1', 'ff02::1', 'fec0::1', '240.0.0.1', '100.64.0.1'])
def test_special_ip_ranges_rejected(address):
    from app.utils.validators import is_public_ip
    assert not is_public_ip(address)


async def test_page_above_old_limit_is_accepted(monkeypatch):
    payload = b'<html><main><p>Readable article.</p></main>' + b' ' * 2_100_000 + b'</html>'
    result = await fetch_mock(lambda request: httpx.Response(200,
        headers={'content-type': 'text/html'}, content=payload), monkeypatch)
    assert len(result.html) > 2_000_000


async def test_compressed_page_is_decoded_once(monkeypatch):
    import gzip
    payload = b'<html><p>Readable content.</p></html>'
    result = await fetch_mock(lambda request: httpx.Response(200,
        headers={'content-type': 'text/html', 'content-encoding': 'gzip'},
        content=gzip.compress(payload)), monkeypatch)
    assert result.html == payload.decode()


async def test_tls_failure_is_useful_error(monkeypatch):
    import ssl
    async def failed(*args):
        raise ssl.SSLError('TLS failure')
    monkeypatch.setattr(scraper, '_fetch', failed)
    with pytest.raises(PipelineError) as error:
        await scraper.fetch_page('https://example.com', Settings())
    assert error.value.status_code == 502
