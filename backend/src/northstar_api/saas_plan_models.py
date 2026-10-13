"""Persisted SaaS plan version models; not yet connected to entitlement resolution."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from northstar_api.database import Base


class SaaSPlan(Base):
    __tablename__ = "saas_plans"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SaaSPlanVersion(Base):
    __tablename__ = "saas_plan_versions"
    __table_args__ = (
        UniqueConstraint("plan_id", "version", name="uq_saas_plan_version"),
        CheckConstraint("version > 0", name="ck_saas_plan_version_positive"),
        CheckConstraint("status IN ('draft', 'published', 'retired')", name="ck_saas_plan_version_status"),
        Index("ix_saas_plan_versions_plan_status", "plan_id", "status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saas_plans.id", ondelete="RESTRICT"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    features_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    quotas_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SaaSPlanPrice(Base):
    __tablename__ = "saas_plan_prices"
    __table_args__ = (
        CheckConstraint("amount_minor >= 0", name="ck_saas_price_nonnegative"),
        CheckConstraint("billing_interval IN ('month', 'year', 'one_time')", name="ck_saas_price_interval"),
        UniqueConstraint("plan_version_id", "currency", "billing_interval", "effective_at", name="uq_saas_price_effective_date"),
        Index("ix_saas_prices_version_effective", "plan_version_id", "effective_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saas_plan_versions.id", ondelete="RESTRICT"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SaaSTenantPlanAssignment(Base):
    __tablename__ = "saas_tenant_plan_assignments"
    __table_args__ = (
        CheckConstraint("expires_at IS NULL OR expires_at > effective_at", name="ck_saas_assignment_dates"),
        Index("ix_saas_assignments_tenant_effective", "tenant_id", "effective_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    plan_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("saas_plan_versions.id", ondelete="RESTRICT"), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
