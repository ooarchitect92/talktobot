"""Explicit release activation gates, independent of provider credential presence."""

from northstar_api.config import get_settings

CAPABILITIES = ("billing", "crm", "channels", "integrations")


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
    for prefix in ("/api/v1", "/v1"):
        if path.startswith(prefix + "/"):
            path = path[len(prefix) :]
            break
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
