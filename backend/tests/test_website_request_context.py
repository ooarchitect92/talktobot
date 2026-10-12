import hashlib
import hmac
import time

from pydantic import SecretStr
from starlette.requests import Request

from northstar_api.config import get_settings
from northstar_api.website_request_context import website_client_address


def test_signed_context_rejects_spoof_expiry_and_wrong_path(monkeypatch):
    secret = "test-only-purpose-limited-context-32-characters"  # noqa: S105 - isolated test fixture
    monkeypatch.setattr(get_settings(), "website_proxy_secret", SecretStr(secret))
    path = "/api/v1/website/inquiries"
    stamp = str(int(time.time()))
    address = "203.0.113.8"
    signature = hmac.new(
        secret.encode(), f"{address}\n{stamp}\nPOST\n{path}".encode(), hashlib.sha256
    ).hexdigest()

    def request(signature_value=signature, timestamp=stamp, request_path=path):
        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": request_path,
                "scheme": "http",
                "server": ("testserver", 80),
                "client": ("172.18.0.2", 443),
                "headers": [
                    (b"x-website-client-ip", address.encode()),
                    (b"x-website-context-time", timestamp.encode()),
                    (b"x-website-context-signature", signature_value.encode()),
                ],
            }
        )

    assert website_client_address(request()) == address
    assert website_client_address(request(signature_value="forged")) == "172.18.0.2"
    assert website_client_address(request(timestamp=str(int(stamp) - 120))) == "172.18.0.2"
    assert website_client_address(request(request_path=path + "/other")) == "172.18.0.2"
