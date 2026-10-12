"""Versioned website owner operations and append-only evidence."""

import sqlalchemy as sa
from alembic import op

revision = "0081_website_owner_operations"
down_revision = "0080_website_cms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "website_posts", sa.Column("workflow_status", sa.String(30), nullable=False, server_default="draft")
    )
    op.add_column("website_posts", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("website_posts", sa.Column("scheduled_actor_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_website_post_scheduled_actor",
        "website_posts",
        "users",
        ["scheduled_actor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column(
        "website_posts",
        sa.Column("editorial_timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
    )
    op.execute("UPDATE website_posts SET workflow_status='published' WHERE status='published'")
    op.create_table(
        "website_resources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("published_document", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "scheduled_actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column("editorial_timezone", sa.String(64), nullable=False),
        sa.UniqueConstraint("kind", "key", name="uq_website_resource_key"),
    )
    op.create_table(
        "website_operations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("resource_id", sa.String(100), nullable=False),
        sa.Column("resource_kind", sa.String(30), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_website_operations_resource_id", "website_operations", ["resource_id"])
    op.create_index("ix_website_operations_occurred_at", "website_operations", ["occurred_at"])
    op.create_table(
        "website_lead_states",
        sa.Column(
            "inquiry_id",
            sa.Uuid(),
            sa.ForeignKey("website_inquiries.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    )
    op.create_table(
        "website_form_submissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "form_id", sa.Uuid(), sa.ForeignKey("website_resources.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("form_version", sa.Integer(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "website_media",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("storage", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "REVOKE ALL ON website_resources, website_operations, website_lead_states, website_form_submissions FROM northstar_app"
        )
        op.execute("GRANT SELECT, INSERT, UPDATE ON website_resources, website_lead_states TO northstar_app")
        op.execute("GRANT SELECT, INSERT ON website_operations, website_form_submissions TO northstar_app")
        op.execute("REVOKE ALL ON website_media FROM northstar_app")
        op.execute("GRANT SELECT, INSERT ON website_media TO northstar_app")


def downgrade() -> None:
    raise RuntimeError("Owner resources and audit evidence require a reviewed preservation migration")
