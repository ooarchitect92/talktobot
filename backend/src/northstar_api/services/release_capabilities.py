"""Explicit release activation gates, independent of provider credential presence."""

import re

from northstar_api.config import get_settings

CAPABILITIES = ("billing", "crm", "channels", "integrations")
PROVIDER_CAPABILITIES = {"telegram": "channels", "zoho": "crm"}
PROVIDERS_BY_CATEGORY = {
    "channels": {
        "telegram",
        "slack",
        "facebook_messenger",
        "instagram",
        "whatsapp",
        "widget",
        "api",
        "custom",
    },
    "crm": {
        "zoho",
        "salesforce",
        "hubspot",
        "dynamics365",
        "pipedrive",
        "freshsales",
        "generic_rest",
        "generic_webhook",
    },
}


def enabled_providers(category: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            provider for provider in PROVIDERS_BY_CATEGORY.get(category, set()) if provider_enabled(provider)
        )
    )


def provider_enabled(provider: str) -> bool:
    capability = PROVIDER_CAPABILITIES.get(provider)
    if capability is None:
        if provider in {"slack", "facebook_messenger", "instagram", "whatsapp", "widget", "api", "custom"}:
            return capability_enabled("channels")
        if provider in {
            "salesforce",
            "hubspot",
            "dynamics365",
            "pipedrive",
            "freshsales",
            "generic_rest",
            "generic_webhook",
        }:
            return capability_enabled("crm")
        return False
    return capability_enabled(capability) or provider in get_settings().enabled_integration_providers


def require_provider(provider: str) -> None:
    if not provider_enabled(provider):
        raise CapabilityUnavailable(f"{provider} is disabled in this release")


def integration_path(path: str) -> str:
    for prefix in (get_settings().app_api_prefix.rstrip("/"), "/v1"):
        if path.startswith(prefix + "/"):
            return path[len(prefix) :]
    return path


def scoped_provider_request(path: str, method: str) -> str | None:
    """Only these paths may bypass a category gate; a scoped dependency checks IDs."""
    path = integration_path(path)
    if method in {"GET", "HEAD", "OPTIONS"}:
        return None
    if re.fullmatch(r"/channels/connections/[0-9a-fA-F-]{36}(?:/(?:agent|test))?", path):
        return "channels"
    if re.fullmatch(
        r"/channels/(?:deliveries/[0-9a-fA-F-]{36}/requeue|webhook-events/[0-9a-fA-F-]{36}/requeue)", path
    ):
        return "channels"
    if re.fullmatch(
        r"/crm/connections/[0-9a-fA-F-]{36}(?:/(?:test|provision|mappings|oauth/start|reconnect|acceptance-test|schema/refresh|workspace-settings))?",
        path,
    ):
        return "crm"
    if re.fullmatch(r"/crm/deliveries/[0-9a-fA-F-]{36}/(?:retry|cancel)", path):
        return "crm"
    return None


class CapabilityUnavailable(RuntimeError):
    """An external operation has not passed release acceptance."""


def require_capability(capability: str) -> None:
    if not capability_enabled(capability):
        raise CapabilityUnavailable(f"{capability} is disabled pending release qualification")


def capability_enabled(capability: str) -> bool:
    settings = get_settings()
    return (
        settings.app_env not in {"production", "staging"}
        or capability in settings.production_verified_capabilities
    )


def disabled_request_capability(path: str, method: str) -> str | None:
    if method == "OPTIONS":
        return None
    path = integration_path(path)
    if path.startswith("/webhooks/channels/"):
        parts = path.split("/")
        return None if len(parts) == 6 and provider_enabled(parts[4]) else "channels"
    if path == "/channels/telegram/connect" and provider_enabled("telegram"):
        return None
    if path in {"/crm/one-click/zoho/start", "/crm/oauth/zoho/callback"} and provider_enabled("zoho"):
        return None
    scoped = scoped_provider_request(path, method)
    if scoped and any(
        provider_enabled(provider)
        for provider, category in PROVIDER_CAPABILITIES.items()
        if category == scoped
    ):
        return None
    if path in {"/billing/checkout", "/billing/portal", "/billing/reactivate", "/billing/webhooks/stripe"}:
        return None if capability_enabled("billing") else "billing"
    for prefix, capability in (
        ("/crm", "crm"),
        ("/channels", "channels"),
        ("/whatsapp", "channels"),
        ("/telegram", "channels"),
        ("/integrations", "integrations"),
    ):
        if path == prefix or path.startswith(prefix + "/"):
            is_mutation = method not in {"GET", "HEAD"} or "/callback" in path or "/oauth" in path
            if is_mutation and not capability_enabled(capability):
                return capability
    return None
