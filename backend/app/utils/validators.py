import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from app.errors import PipelineError


@dataclass(frozen=True)
class Destination:
    url: str
    hostname: str
    port: int
    addresses: tuple[str, ...]


def normalize_url(value: str) -> str:
    value = value.strip()
    try:
        if re.search(r'[\x00-\x20\x7f\\]', value):
            raise ValueError()
        parts = urlsplit(value)
        if parts.scheme not in {'http', 'https'} or not parts.hostname:
            raise ValueError()
        if parts.username is not None or parts.password is not None:
            raise ValueError()
        hostname = parts.hostname.encode('idna').decode('ascii').lower().rstrip('.')
        if not hostname or '%' in hostname:
            raise ValueError()
        port = parts.port or (443 if parts.scheme == 'https' else 80)
        if port not in {80, 443}:
            raise ValueError()
        host = f'[{hostname}]' if ':' in hostname else hostname
        netloc = host + (f':{parts.port}' if parts.port else '')
        return urlunsplit((parts.scheme, netloc, parts.path or '/', parts.query, ''))
    except (ValueError, UnicodeError):
        raise PipelineError(400, 'Enter a valid public HTTP or HTTPS URL using port 80 or 443.') from None


def is_public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    if isinstance(address, ipaddress.IPv6Address):
        # Reject mapped and transition addresses to prevent embedded IPv4 bypasses.
        if address.ipv4_mapped or address.sixtofour or address.teredo:
            return False
    return address.is_global and not (
        address.is_multicast or address.is_reserved or address.is_unspecified
        or address.is_loopback or address.is_link_local
        or getattr(address, 'is_site_local', False)
    )


async def validate_destination(value: str) -> Destination:
    url = normalize_url(value)
    parts = urlsplit(url)
    hostname = parts.hostname
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    if hostname == 'localhost' or hostname.endswith(('.localhost', '.local', '.internal')):
        raise PipelineError(400, 'Private or local network destinations are not allowed.')
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            records = await asyncio.get_running_loop().getaddrinfo(
                hostname, port, type=socket.SOCK_STREAM,
            )
        except socket.gaierror:
            raise PipelineError(502, 'Unable to resolve this website.') from None
        addresses = tuple(dict.fromkeys(record[4][0] for record in records))
    else:
        addresses = (str(literal),)
    if not addresses or not all(is_public_ip(address) for address in addresses):
        raise PipelineError(400, 'Private or local network destinations are not allowed.')
    return Destination(url, hostname, port, addresses)
