"""Schema safety tests for additive SaaS catalogue migration."""
from northstar_api.saas_plan_models import SaaSPlan, SaaSPlanVersion, SaaSPlanPrice, SaaSTenantPlanAssignment


def test_plan_schema_has_immutable_version_identity() -> None:
    assert {"plan_id", "version", "status", "features_json", "quotas_json"} <= set(SaaSPlanVersion.__table__.columns.keys())
    assert {"currency", "amount_minor", "effective_at", "billing_interval"} <= set(SaaSPlanPrice.__table__.columns.keys())


def test_plan_assignment_requires_tenant_and_version() -> None:
    assert not SaaSTenantPlanAssignment.__table__.c.tenant_id.nullable
    assert not SaaSTenantPlanAssignment.__table__.c.plan_version_id.nullable


def test_catalog_has_unique_plan_code() -> None:
    assert SaaSPlan.__table__.c.code.unique
