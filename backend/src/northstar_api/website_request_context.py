"""Purpose-limited abuse context from the authenticated website gateway."""

from __future__ import annotations

import hashlib
import hmac
import time
from ipaddress import IPv6Address, ip_address

from fastapi import Request

from northstar_api.config import get_settings


def website_client_address(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    secret = get_settings().website_proxy_secret
    claimed = request.headers.get("x-website-client-ip", "")
    stamp = request.headers.get("x-website-context-time", "")
    signature = request.headers.get("x-website-context-signature", "")
    if not secret or len(secret.get_secret_value()) < 32 or not claimed or not stamp:
        return peer
    try:
        address = ip_address(claimed)
        if abs(time.time() - int(stamp)) > 60:
            return peer
        message = f"{claimed}\n{stamp}\n{request.method}\n{request.url.path}"
        expected = hmac.new(secret.get_secret_value().encode(), message.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return peer
        return str(address.ipv4_mapped or address) if isinstance(address, IPv6Address) else str(address)
    except ValueError:
        return peer
