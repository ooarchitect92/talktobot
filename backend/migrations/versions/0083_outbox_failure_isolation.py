"""Persist outbox retry state without changing the at-least-once delivery contract."""

import sqlalchemy as sa
from alembic import op

revision = "0083_outbox_failure_isolation"
down_revision = "0082_service_audit_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("outbox_events")}
    for name in ("next_attempt_at", "dead_lettered_at"):
        if name not in columns:
            op.add_column("outbox_events", sa.Column(name, sa.DateTime(timezone=True), nullable=True))
    indexes = {index["name"] for index in inspector.get_indexes("outbox_events")}
    if "ix_outbox_pending_stream" in indexes:
        return
    op.create_index(
        "ix_outbox_pending_stream",
        "outbox_events",
        ["tenant_id", "aggregate_type", "aggregate_id", "occurred_at", "id"],
        postgresql_where=sa.text("published_at IS NULL"),
        sqlite_where=sa.text("published_at IS NULL"),
    )


def downgrade() -> None:
    raise RuntimeError("Roll back application images; retain retry state and quarantine evidence")
