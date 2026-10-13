"""Add immutable, versioned owner-managed subscription plan catalogue.

The existing tenant_subscriptions and legacy entitlement resolver remain unchanged.
This is additive schema only; it does not activate pricing changes.
"""
import sqlalchemy as sa
from alembic import op

revision = "0084_versioned_plan_catalog"
down_revision = "0083_outbox_failure_isolation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saas_plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False, unique=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "saas_plan_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("plan_id", sa.Uuid(), sa.ForeignKey("saas_plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("features_json", sa.JSON(), nullable=False),
        sa.Column("quotas_json", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("plan_id", "version", name="uq_saas_plan_version"),
        sa.CheckConstraint("version > 0", name="ck_saas_plan_version_positive"),
        sa.CheckConstraint("status IN ('draft', 'published', 'retired')", name="ck_saas_plan_version_status"),
    )
    op.create_index("ix_saas_plan_versions_plan_status", "saas_plan_versions", ["plan_id", "status"])
    op.create_table(
        "saas_plan_prices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("plan_version_id", sa.Uuid(), sa.ForeignKey("saas_plan_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("billing_interval", sa.String(20), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_minor >= 0", name="ck_saas_price_nonnegative"),
        sa.CheckConstraint("billing_interval IN ('month', 'year', 'one_time')", name="ck_saas_price_interval"),
        sa.UniqueConstraint("plan_version_id", "currency", "billing_interval", "effective_at", name="uq_saas_price_effective_date"),
    )
    op.create_index("ix_saas_prices_version_effective", "saas_plan_prices", ["plan_version_id", "effective_at"])
    op.create_table(
        "saas_tenant_plan_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_version_id", sa.Uuid(), sa.ForeignKey("saas_plan_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("expires_at IS NULL OR expires_at > effective_at", name="ck_saas_assignment_dates"),
    )
    op.create_index("ix_saas_assignments_tenant_effective", "saas_tenant_plan_assignments", ["tenant_id", "effective_at"])


def downgrade() -> None:
    # Retain contract history if downgrading app images. Dropping immutable
    # prices and assignments could destroy billing/authorization evidence.
    raise RuntimeError("Retain SaaS contract history; roll back application code instead")
