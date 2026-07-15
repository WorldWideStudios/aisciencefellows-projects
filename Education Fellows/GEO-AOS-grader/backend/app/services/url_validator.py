"""Безопасная валидация публичных URL."""
from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


class InvalidURLError(Exception):
    pass


def validate_public_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError("URL должен начинаться с http:// или https://")
    host = (parsed.hostname or "").lower()
    if not host:
        raise InvalidURLError("URL не содержит хост")
    if host in ("localhost", "localhost.localdomain"):
        raise InvalidURLError("Локальные адреса не разрешены")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise InvalidURLError("Приватные IP-адреса не разрешены")
    except ValueError:
        pass
    return raw_url
