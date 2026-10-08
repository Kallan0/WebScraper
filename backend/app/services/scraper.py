import asyncio
import ssl
import logging
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
from app.config import Settings
from app.errors import PipelineError
from app.utils.validators import validate_destination


@dataclass(frozen=True)
class ScrapedPage:
    url: str
    html: str


async def fetch_page(url: str, settings: Settings) -> ScrapedPage:
    try:
        async with asyncio.timeout(settings.request_timeout):
            async with httpx.AsyncClient(
                timeout=settings.request_timeout, follow_redirects=False, trust_env=False,
            ) as client:
                return await _fetch(client, url, settings)
    except (TimeoutError, httpx.TimeoutException):
        raise PipelineError(504, 'The website took too long to respond.') from None
    except (httpx.HTTPError, ssl.SSLError, UnicodeError):
        raise PipelineError(502, 'Unable to fetch this webpage.') from None


async def _fetch(client: httpx.AsyncClient, url: str, settings: Settings) -> ScrapedPage:
    for hop in range(settings.max_redirects + 1):
        destination = await validate_destination(url)
        # Connect to a validated IP, preserving Host and TLS server name.
        # A second DNS lookup cannot redirect the connection to a private address.
        pinned = httpx.URL(destination.url).copy_with(host=destination.addresses[0])
        host = httpx.URL(destination.url).netloc.decode('ascii')
        async with client.stream(
            'GET', pinned,
            headers={'Host': host, 'User-Agent': settings.scraper_user_agent,
                     'Accept': 'text/html,application/xhtml+xml', 'Accept-Encoding': 'gzip, deflate'},
            extensions={'sni_hostname': destination.hostname},
        ) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get('location')
                if not location or hop == settings.max_redirects:
                    raise PipelineError(502, 'This website has an invalid redirect or too many redirects.')
                url = urljoin(destination.url, location)
                continue
            if response.status_code >= 400:
                logging.getLogger(__name__).warning(
                    'Website fetch failed: host=%s status=%s', destination.hostname, response.status_code,
                )
                if response.status_code in {401, 403}:
                    raise PipelineError(502,
                        f'The website denied access (HTTP {response.status_code}). It may require sign-in '
                        'or block automated requests from hosting providers. Try another public source.')
                if response.status_code == 429:
                    raise PipelineError(429,
                        'The website is rate-limiting requests (HTTP 429). Wait before trying again.')
                if response.status_code == 404:
                    raise PipelineError(422, 'The webpage was not found (HTTP 404). Check the article URL.')
                raise PipelineError(502,
                    f'The website returned HTTP {response.status_code}. Please try again later.')
            if not 200 <= response.status_code < 300:
                raise PipelineError(502, 'The website returned an unsupported response.')
            content_type = response.headers.get('content-type', '').split(';')[0].strip().lower()
            if content_type not in {'text/html', 'application/xhtml+xml'}:
                raise PipelineError(422, 'Only HTML webpages are supported.')
            declared = response.headers.get('content-length', '')
            if declared.isdigit() and int(declared) > settings.max_response_bytes:
                raise PipelineError(422, f'This webpage exceeds the {settings.max_response_bytes / 1_000_000:g} MB HTML download limit. Try a smaller page or increase MAX_RESPONSE_BYTES in backend/.env.')
            body = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=16_384):
                body.extend(chunk)
                if len(body) > settings.max_response_bytes:
                    raise PipelineError(422, f'This webpage exceeds the {settings.max_response_bytes / 1_000_000:g} MB HTML download limit. Try a smaller page or increase MAX_RESPONSE_BYTES in backend/.env.')
            # Let HTTPX handle charset decoding without an additional network call.
            decoded = httpx.Response(
                200, headers={'content-type': response.headers['content-type']}, content=bytes(body),
            )
            return ScrapedPage(destination.url, decoded.text)
    raise PipelineError(502, 'Too many redirects.')
