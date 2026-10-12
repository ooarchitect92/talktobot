"""Restrict global help writes and preserve background service audit evidence."""

from alembic import op
from sqlalchemy import text

revision = "0082_service_audit_permissions"
down_revision = "0081_website_owner_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    if bind.execute(text("SELECT 1 FROM pg_roles WHERE rolname = 'northstar_service'")).scalar():
        op.execute(
            "REVOKE UPDATE, DELETE, TRUNCATE ON integration_audit_events, website_revisions, "
            "website_operations, website_form_submissions FROM northstar_service"
        )
        op.execute("REVOKE ALL ON alembic_version FROM northstar_service")
    op.execute("REVOKE ALL ON alembic_version FROM northstar_app")
    op.execute("REVOKE ALL ON help_categories, help_articles, help_article_chunks FROM northstar_app")
    op.execute("GRANT SELECT ON help_categories, help_articles, help_article_chunks TO northstar_app")


def downgrade() -> None:
    raise RuntimeError("Restoring audit mutation privileges requires an explicit security review")
