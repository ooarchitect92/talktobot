from northstar_api.config import get_settings
from northstar_api.services.release_capabilities import capability_enabled, disabled_request_capability


def test_provider_activation_does_not_enable_categories_or_other_providers(monkeypatch):
    from northstar_api.services.release_capabilities import provider_enabled

    monkeypatch.setattr(get_settings(), "app_env", "staging")
    monkeypatch.setattr(get_settings(), "production_verified_capabilities", [])
    monkeypatch.setattr(get_settings(), "enabled_integration_providers", ["telegram", "zoho"])
    assert provider_enabled("telegram") and provider_enabled("zoho")
    assert not provider_enabled("hubspot") and not provider_enabled("whatsapp")
    assert not capability_enabled("crm") and not capability_enabled("channels")
    assert disabled_request_capability("/api/v1/channels/telegram/connect", "POST") is None
    assert disabled_request_capability("/api/v1/channels/telegram/connect/start", "POST") == "channels"
    assert disabled_request_capability("/api/v1/crm/one-click/zoho/start", "POST") is None
    assert disabled_request_capability("/api/v1/crm/one-click/hubspot/start", "POST") == "crm"
    assert disabled_request_capability("/api/v1/crm/oauth/zoho/callback", "GET") is None
    assert disabled_request_capability("/api/v1/crm/oauth/hubspot/callback", "GET") == "crm"
    assert disabled_request_capability("/api/v1/webhooks/channels/tenant/telegram/id", "POST") is None
    assert disabled_request_capability("/api/v1/webhooks/channels/tenant/instagram/id", "POST") == "channels"
    assert disabled_request_capability("/api/v1/crm/connections", "POST") == "crm"


async def test_provider_guard_checks_connection_scope_before_mutation(client, auth_headers, monkeypatch):
    from uuid import uuid4

    ids = {}
    for provider in ("zoho", "hubspot"):
        response = await client.post(
            "/api/v1/crm/connections",
            headers=auth_headers,
            json={"provider": provider, "name": f"gate-{provider}-{uuid4().hex}"},
        )
        assert response.status_code == 201, response.text
        ids[provider] = response.json()["id"]
    monkeypatch.setattr(get_settings(), "app_env", "staging")
    monkeypatch.setattr(get_settings(), "mfa_required", False)
    monkeypatch.setattr(get_settings(), "production_verified_capabilities", [])
    monkeypatch.setattr(get_settings(), "enabled_integration_providers", ["telegram", "zoho"])
    denied = await client.delete(f"/api/v1/crm/connections/{ids['hubspot']}", headers=auth_headers)
    assert denied.status_code == 503, denied.text
    missing = await client.delete(f"/api/v1/crm/connections/{uuid4()}", headers=auth_headers)
    assert missing.status_code == 404, missing.text
    anonymous = await client.delete(f"/api/v1/crm/connections/{ids['zoho']}")
    assert anonymous.status_code == 401, anonymous.text
    allowed = await client.delete(f"/api/v1/crm/connections/{ids['zoho']}", headers=auth_headers)
    assert allowed.status_code == 204, allowed.text


def test_production_capabilities_fail_closed(monkeypatch):
    monkeypatch.setattr(get_settings(), "app_env", "production")
    monkeypatch.setattr(get_settings(), "production_verified_capabilities", [])
    assert not capability_enabled("billing")
    assert disabled_request_capability("/api/v1/billing/checkout", "POST") == "billing"
    assert disabled_request_capability("/v1/billing/webhooks/stripe", "POST") == "billing"
    assert disabled_request_capability("/api/v1/crm/oauth/zoho/callback", "GET") == "crm"
    assert disabled_request_capability("/api/v1/channels/connections", "POST") == "channels"
    assert disabled_request_capability("/api/v1/billing/subscription", "GET") is None
    assert disabled_request_capability("/api/v1/billing/cancel", "POST") is None
    assert disabled_request_capability("/api/v1/website/forms/contact/submit", "POST") is None


def test_activation_only_enables_approved_capability(monkeypatch):
    monkeypatch.setattr(get_settings(), "app_env", "staging")
    monkeypatch.setattr(get_settings(), "production_verified_capabilities", ["crm"])
    assert disabled_request_capability("/api/v1/crm/connections", "POST") is None
    assert disabled_request_capability("/api/v1/billing/checkout", "POST") == "billing"


async def test_disabled_provider_cannot_send_from_a_background_call(monkeypatch):
    import pytest

    from northstar_api.services.release_capabilities import CapabilityUnavailable
    from northstar_api.services.telegram import TelegramBotClient
    from northstar_api.services.whatsapp import WhatsAppCloudClient

    monkeypatch.setattr(get_settings(), "app_env", "staging")
    monkeypatch.setattr(get_settings(), "production_verified_capabilities", [])
    with pytest.raises(CapabilityUnavailable):
        await TelegramBotClient().get_me("synthetic-token")
    with pytest.raises(CapabilityUnavailable):
        await WhatsAppCloudClient()._request("POST", "messages", operation="send")


def test_deployed_kafka_rejects_plaintext(monkeypatch):
    import pytest

    from northstar_api.services.kafka_transport import kafka_transport_options

    monkeypatch.setattr(get_settings(), "app_env", "staging")
    monkeypatch.setattr(get_settings(), "kafka_security_protocol", "PLAINTEXT")
    with pytest.raises(ValueError, match="TLS"):
        kafka_transport_options()


async def test_disabled_crm_blocks_before_outbound_resolution(monkeypatch):
    from unittest.mock import AsyncMock

    import pytest

    from northstar_api.lead_crm.safe_http import request_public
    from northstar_api.services import safe_fetch
    from northstar_api.services.release_capabilities import CapabilityUnavailable

    monkeypatch.setattr(get_settings(), "app_env", "staging")
    monkeypatch.setattr(get_settings(), "production_verified_capabilities", [])
    resolve = AsyncMock()
    monkeypatch.setattr(safe_fetch, "_resolve_public_target", resolve)
    with pytest.raises(CapabilityUnavailable):
        await request_public("POST", "https://crm.example.test/records")
    resolve.assert_not_called()


def test_disabled_billing_never_grants_stored_paid_entitlements(monkeypatch):
    from northstar_api.entitlements import entitlement_for_plan

    monkeypatch.setattr(get_settings(), "app_env", "staging")
    monkeypatch.setattr(get_settings(), "production_verified_capabilities", [])
    free = entitlement_for_plan("free")
    for plan in ("starter", "professional", "enterprise", "legacy_custom_contract"):
        assert entitlement_for_plan(plan) == free
    assert not free.crm_enabled and not free.custom_domain_enabled


def test_scram_requires_credentials_and_verifies_tls(monkeypatch):
    import ssl

    import pytest
    from pydantic import SecretStr

    from northstar_api.services.kafka_transport import kafka_transport_options

    monkeypatch.setattr(get_settings(), "kafka_security_protocol", "SASL_SSL")
    monkeypatch.setattr(get_settings(), "kafka_sasl_username", "")
    with pytest.raises(ValueError, match="credentials"):
        kafka_transport_options()
    monkeypatch.setattr(get_settings(), "kafka_sasl_username", "fixture")
    monkeypatch.setattr(get_settings(), "kafka_sasl_password", SecretStr("synthetic-not-deployed"))
    options = kafka_transport_options()
    assert options["ssl_context"].verify_mode == ssl.CERT_REQUIRED
    assert options["ssl_context"].check_hostname
    assert options["sasl_mechanism"] == "SCRAM-SHA-512"
