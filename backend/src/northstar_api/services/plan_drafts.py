"""Immutable plan-draft validation used before future owner pricing writes.

This module does not alter existing subscription resolution or payment handling.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Mapping


class PlanDraftError(ValueError):
    """Invalid proposed subscription plan configuration."""


@dataclass(frozen=True, slots=True)
class PlanPriceDraft:
    currency: str
    amount_minor: int
    interval: str
    effective_at: datetime

    @classmethod
    def validate(
        cls, *, currency: str, amount_minor: int, interval: str, effective_at: datetime
    ) -> "PlanPriceDraft":
        currency = currency.strip().upper()
        if len(currency) != 3 or not currency.isascii() or not currency.isalpha():
            raise PlanDraftError("currency must be a three-letter ISO currency code")
        if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor < 0:
            raise PlanDraftError("amount_minor must be a nonnegative integer")
        if amount_minor > 10**12:
            raise PlanDraftError("amount_minor exceeds the supported maximum")
        if interval not in {"month", "year", "one_time"}:
            raise PlanDraftError("Unsupported billing interval")
        if effective_at.tzinfo is None or effective_at.utcoffset() is None:
            raise PlanDraftError("effective_at must have a timezone")
        return cls(currency, amount_minor, interval, effective_at.astimezone(timezone.utc))


@dataclass(frozen=True, slots=True)
class PlanVersionDraft:
    code: str
    features: frozenset[str]
    quotas: tuple[tuple[str, int | None], ...]

    @classmethod
    def validate(
        cls,
        *,
        code: str,
        features: list[str],
        quotas: Mapping[str, int | None],
        permitted_features: frozenset[str],
        permitted_quotas: frozenset[str],
    ) -> "PlanVersionDraft":
        if not code or len(code) > 40 or not all(c.islower() or c.isdigit() or c in "_-" for c in code):
            raise PlanDraftError("Plan code must use lowercase letters, digits, underscores or hyphens")
        if len(features) != len(set(features)):
            raise PlanDraftError("Duplicate features are not allowed")
        if not set(features) <= permitted_features:
            raise PlanDraftError("Unknown feature in plan")
        if not set(quotas) <= permitted_quotas:
            raise PlanDraftError("Unknown quota in plan")
        for value in quotas.values():
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise PlanDraftError("Quotas must be nonnegative integers or null for unlimited")
        return cls(code=code, features=frozenset(features), quotas=tuple(sorted(quotas.items())))
