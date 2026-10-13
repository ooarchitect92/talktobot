from datetime import UTC, datetime

import pytest

from northstar_api.services.plan_drafts import PlanDraftError, PlanPriceDraft, PlanVersionDraft


def test_price_requires_minor_units_and_aware_date() -> None:
    now = datetime(2026, 10, 14, tzinfo=UTC)
    price = PlanPriceDraft.validate(currency="inr", amount_minor=299900, interval="month", effective_at=now)
    assert price.currency == "INR"
    assert price.amount_minor == 299900
    with pytest.raises(PlanDraftError):
        PlanPriceDraft.validate(currency="INR", amount_minor=-1, interval="month", effective_at=now)
    with pytest.raises(PlanDraftError):
        PlanPriceDraft.validate(currency="INR", amount_minor=1, interval="month", effective_at=datetime(2026, 10, 14))
    with pytest.raises(PlanDraftError):
        PlanPriceDraft.validate(currency="INR", amount_minor=True, interval="month", effective_at=now)


def test_plan_draft_rejects_unknown_permissions_and_negative_quotas() -> None:
    allowed = frozenset({"crm", "api"})
    quotas = frozenset({"agents", "tokens"})
    valid = PlanVersionDraft.validate(
        code="growth", features=["crm"], quotas={"agents": 5, "tokens": None},
        permitted_features=allowed, permitted_quotas=quotas,
    )
    assert valid.features == frozenset({"crm"})
    with pytest.raises(PlanDraftError):
        PlanVersionDraft.validate(code="growth", features=["admin.superuser"], quotas={},
                                  permitted_features=allowed, permitted_quotas=quotas)
    with pytest.raises(PlanDraftError):
        PlanVersionDraft.validate(code="growth", features=["crm", "crm"], quotas={},
                                  permitted_features=allowed, permitted_quotas=quotas)
    with pytest.raises(PlanDraftError):
        PlanVersionDraft.validate(code="growth", features=[], quotas={"agents": -1},
                                  permitted_features=allowed, permitted_quotas=quotas)
