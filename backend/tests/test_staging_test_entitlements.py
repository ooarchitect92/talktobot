from uuid import uuid4

from northstar_api.config import get_settings
from northstar_api.services.entitlements import effective_plan_for_tenant, effective_policy_for_tenant
from northstar_api.services.release_capabilities import capability_enabled


def test_full_access_applies_only_to_allowlisted_staging_tenant(monkeypatch):
    settings = get_settings()
    tenant = uuid4()
    monkeypatch.setattr(settings, "app_env", "staging")
    monkeypatch.setattr(settings, "production_verified_capabilities", [])
    monkeypatch.setattr(settings, "staging_full_access_tenant_ids", [tenant])
    assert effective_plan_for_tenant(tenant, "free") == "enterprise_test"
    assert effective_plan_for_tenant(uuid4(), "enterprise") == "free"
    policy = effective_policy_for_tenant(tenant, "free")
    assert policy.workspace_limit is None
    assert policy.agent_limit is None
    assert policy.member_limit is None
    assert policy.token_limit_monthly is None
    assert policy.api_enabled is True
    assert effective_policy_for_tenant(uuid4(), "enterprise").token_limit_monthly == 10_000
    assert capability_enabled("billing") is False
    assert capability_enabled("integrations") is False


def test_staging_allowlist_never_grants_production_entitlements(monkeypatch):
    settings = get_settings()
    tenant = uuid4()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "production_verified_capabilities", [])
    monkeypatch.setattr(settings, "staging_full_access_tenant_ids", [tenant])
    assert effective_plan_for_tenant(tenant, "enterprise") == "free"
