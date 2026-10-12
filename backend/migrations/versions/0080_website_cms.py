"""Single-site public content, preserved revisions and accepted enquiries."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0080_website_cms"
down_revision = "0079_lead_workspace_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "website_posts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("published_document", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "website_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "post_id", sa.Uuid(), sa.ForeignKey("website_posts.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_website_revisions_post", "website_revisions", ["post_id", "created_at"])
    op.create_table(
        "website_inquiries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    if op.get_bind().dialect.name == "postgresql":
        # Existing default privileges may grant UPDATE/DELETE on every new table.
        # Remove them explicitly before granting the CMS's narrower privileges.
        op.execute("REVOKE ALL ON website_posts, website_revisions, website_inquiries FROM northstar_app")
        op.execute("GRANT SELECT, INSERT, UPDATE ON website_posts TO northstar_app")
        op.execute("GRANT SELECT, INSERT ON website_revisions, website_inquiries TO northstar_app")


def downgrade() -> None:
    raise RuntimeError(
        "Website source and revision history must not be automatically deleted. Restore a backup or perform a reviewed migration."
    )
