"""Contract tests for SaaS progress accounting and owner-plan boundaries.

These tests deliberately avoid network and database dependencies. The runtime
plan-write implementation will be introduced only after migration review.
"""
from __future__ import annotations

import json
from pathlib import Path

from northstar_api.entitlements import PLAN_ENTITLEMENTS, UNKNOWN_PLAN_ENTITLEMENT, entitlement_for_plan
from northstar_api.routers.platform_admin import get_platform_entitlements, require_platform_permissions


def test_unknown_plan_cannot_inherit_paid_entitlements() -> None:
    unknown = entitlement_for_plan("unregistered_premium_plan")
    assert unknown == UNKNOWN_PLAN_ENTITLEMENT
    assert unknown.agent_limit == 0
    assert not unknown.api_enabled
    assert not unknown.allowed_channels


def test_existing_plan_catalog_has_distinct_named_policies() -> None:
    assert {"free", "starter", "professional", "business", "enterprise"} <= set(PLAN_ENTITLEMENTS)
    assert PLAN_ENTITLEMENTS["free"].agent_limit <= PLAN_ENTITLEMENTS["business"].agent_limit


def test_platform_plan_reader_has_explicit_permission_dependency() -> None:
    dep = require_platform_permissions("platform.system.read")
    assert callable(dep)


def test_progress_registry_has_consistent_weighting() -> None:
    root = Path(__file__).resolve().parents[2]
    registry = json.loads((root / "docs" / "quality" / "implementation-progress.json").read_text())
    assert registry["repository"] == "ooarchitect92/talktobot"
    assert sum(item["weight"] for item in registry["workstreams"]) == 100
    assert all(0 <= item["estimated_completion"] <= 100 for item in registry["workstreams"])
    assert registry["production_release_authorized"] is False
