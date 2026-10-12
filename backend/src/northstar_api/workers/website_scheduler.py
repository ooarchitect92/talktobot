"""Resume durable, human-approved website schedules after restarts."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import structlog
from fastapi import HTTPException
from sqlalchemy import select, text

from northstar_api.config import get_settings
from northstar_api.database import SessionFactory
from northstar_api.models import Role, User
from northstar_api.security import Principal
from northstar_api.services.email_verification import email_is_verified
from northstar_api.website import ActionInput, WebsitePost, act_on_post, editor_roles, revision
from northstar_api.website_operations import ResourceAction, WebsiteResource, audit, resource_action

logger = structlog.get_logger(__name__)


async def tick() -> int:
    settings = get_settings()
    async with SessionFactory() as session:
        if session.get_bind().dialect.name == "postgresql":
            await session.execute(text("SELECT pg_advisory_xact_lock(74193081)"))
        rows = list(
            await session.scalars(
                select(WebsiteResource)
                .where(
                    WebsiteResource.status == "scheduled", WebsiteResource.scheduled_at <= datetime.now(UTC)
                )
                .order_by(WebsiteResource.scheduled_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        )
        completed = 0
        for row in rows:
            allowed = {
                email.strip().lower() for email in settings.website_editor_emails.split(",") if email.strip()
            }
            if not settings.is_production and settings.seed_admin_email:
                allowed.add(str(settings.seed_admin_email).lower())
            actor_id = row.scheduled_actor_id
            user = await session.get(User, actor_id) if actor_id else None
            if (
                not user
                or not user.is_active
                or not await email_is_verified(session, user.id)
                or user.email.lower() not in allowed
                or "publisher" not in editor_roles(user.email)
                or (settings.requires_mfa and not user.mfa_enabled)
            ):
                row.status = "publication_failed"
                row.version += 1
                audit(
                    session,
                    str(row.id),
                    row.kind,
                    "schedule_denied",
                    row.version,
                    actor_id,
                    {"reason_code": "actor_not_authorized"},
                    "Scheduled actor no longer has publishing access",
                )
                await session.commit()
                continue
            principal = Principal(
                user_id=user.id,
                tenant_id=UUID(int=0),
                role=Role.OWNER,
                token_id=f"scheduled-operation:{row.id}:{row.version}",
            )
            row_id, version, kind = row.id, row.version, row.kind
            try:
                await resource_action(
                    row_id,
                    ResourceAction(
                        version=version,
                        action="publish",
                        reason="Owner-approved schedule; executor=website-scheduler",
                    ),
                    session,
                    principal,
                )
                completed += 1
            except HTTPException as error:
                await session.rollback()
                failed = await session.get(WebsiteResource, row_id)
                if failed and failed.version == version and failed.status == "scheduled":
                    failed.status = "publication_failed"
                    failed.version += 1
                    audit(
                        session,
                        str(row_id),
                        kind,
                        "schedule_failed",
                        failed.version,
                        actor_id,
                        {"http_status": error.status_code},
                        "Scheduled publication failed validation; previous live revision is preserved",
                    )
                    await session.commit()
        posts = list(
            await session.scalars(
                select(WebsitePost)
                .where(
                    WebsitePost.workflow_status == "scheduled", WebsitePost.scheduled_at <= datetime.now(UTC)
                )
                .order_by(WebsitePost.scheduled_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        )
        for post in posts:
            allowed = {
                email.strip().lower() for email in settings.website_editor_emails.split(",") if email.strip()
            }
            if not settings.is_production and settings.seed_admin_email:
                allowed.add(str(settings.seed_admin_email).lower())
            actor_id = post.scheduled_actor_id
            user = await session.get(User, actor_id) if actor_id else None
            if (
                not user
                or not user.is_active
                or not await email_is_verified(session, user.id)
                or user.email.lower() not in allowed
                or "publisher" not in editor_roles(user.email)
                or (settings.requires_mfa and not user.mfa_enabled)
            ):
                post.workflow_status = "publication_failed"
                post.version += 1
                audit(
                    session,
                    str(post.id),
                    "post",
                    "schedule_denied",
                    post.version,
                    actor_id,
                    {"reason_code": "actor_not_authorized"},
                    "Scheduled actor no longer has publishing access",
                )
                await session.commit()
                continue
            principal = Principal(
                user_id=user.id,
                tenant_id=UUID(int=0),
                role=Role.OWNER,
                token_id=f"scheduled-article:{post.id}:{post.version}",
            )
            post_id, version = post.id, post.version
            try:
                await act_on_post(
                    post_id,
                    ActionInput(
                        version=version,
                        action="publish",
                        reason="Owner-approved schedule; executor=website-scheduler",
                    ),
                    session,
                    principal,
                )
                completed += 1
            except HTTPException as error:
                await session.rollback()
                failed_post = await session.get(WebsitePost, post_id)
                if (
                    failed_post
                    and failed_post.version == version
                    and failed_post.workflow_status == "scheduled"
                ):
                    failed_post.workflow_status = "publication_failed"
                    failed_post.version += 1
                    revision(
                        session,
                        failed_post,
                        principal,
                        "schedule_failed",
                        f"Validation failed ({error.status_code}); previous live revision preserved",
                    )
                    await session.commit()
        return completed


async def main() -> None:
    # Import the app's complete model registry before configuring ORM relationships.
    from northstar_api.main import app  # noqa: F401

    while True:
        try:
            count = await tick()
            if count:
                logger.info("website_schedules_published", count=count)
        except Exception as error:
            logger.error("website_scheduler_unavailable", error_type=type(error).__name__)
        await asyncio.sleep(20)


if __name__ == "__main__":
    asyncio.run(main())
