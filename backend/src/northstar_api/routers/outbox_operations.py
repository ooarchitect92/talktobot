"""Explicit, scoped, step-up protected recovery of retained outbox events."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import ConfigDict, Field, SecretStr
from sqlalchemy import select

from northstar_api.dependencies import DBSession
from northstar_api.lead_crm.audit import record_audit_event
from northstar_api.models import OutboxEvent, User
from northstar_api.routers.platform_admin import PlatformRuntimeManagePrincipal, PlatformSystemReadPrincipal
from northstar_api.schemas import APIModel
from northstar_api.security import verify_password
from northstar_api.services.mfa import MFAError, consume_mfa_factor
from northstar_api.services.rate_limit import redis_services

router = APIRouter(prefix="/platform-admin/outbox", tags=["platform outbox"])


class ReplayInput(APIModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: UUID
    expected_attempts: int = Field(ge=1)
    reason: str = Field(min_length=10, max_length=500)
    current_password: SecretStr = Field(min_length=1, max_length=1024)
    code: str = Field(pattern=r"^\d{6}$")


@router.get("")
async def list_retained_events(
    tenant_id: UUID,
    session: DBSession,
    principal: PlatformSystemReadPrincipal,
    response: Response,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[dict[str, object]]:
    response.headers["Cache-Control"] = "no-store"
    rows = await session.scalars(
        select(OutboxEvent)
        .where(OutboxEvent.tenant_id == tenant_id, OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.occurred_at, OutboxEvent.id)
        .limit(limit)
    )
    return [
        {
            "id": str(row.id),
            "eventType": row.event_type,
            "aggregateType": row.aggregate_type,
            "aggregateId": row.aggregate_id,
            "attempts": row.attempts,
            "lastError": row.last_error,
            "nextAttemptAt": row.next_attempt_at,
            "quarantinedAt": row.dead_lettered_at,
        }
        for row in rows
    ]


@router.post("/{event_id}/retry")
async def retry_retained_event(
    event_id: UUID,
    payload: ReplayInput,
    session: DBSession,
    principal: PlatformRuntimeManagePrincipal,
    request: Request,
    response: Response,
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    rate = await redis_services.check_rate_limit(f"outbox-recovery:{principal.user_id}", 5, scope="auth")
    if not rate.allowed:
        raise HTTPException(429, "Recovery verification rate limit exceeded")
    user = await session.get(User, principal.user_id)
    if user is None or not await asyncio.to_thread(
        verify_password, payload.current_password.get_secret_value(), user.password_hash
    ):
        raise HTTPException(401, "Recent password and authenticator verification are required")
    try:
        await consume_mfa_factor(session, principal.user_id, code=payload.code)
    except MFAError:
        raise HTTPException(401, "Recent password and authenticator verification are required") from None
    row = await session.scalar(
        select(OutboxEvent)
        .where(OutboxEvent.id == event_id, OutboxEvent.tenant_id == payload.tenant_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise HTTPException(404, "Retained event not found in the selected tenant")
    if row.published_at or not row.dead_lettered_at or row.attempts != payload.expected_attempts:
        raise HTTPException(409, "Event state changed; reload before requesting recovery")
    before = {
        "attempts": row.attempts,
        "error": row.last_error,
        "quarantinedAt": row.dead_lettered_at.isoformat(),
    }
    row.next_attempt_at = datetime.now(UTC)
    row.dead_lettered_at = None
    row.attempts = 0
    row.last_error = None
    record_audit_event(
        session,
        tenant_id=row.tenant_id,
        actor_user_id=principal.user_id,
        action="platform.outbox.retry",
        entity_type="outbox_event",
        entity_id=str(row.id),
        category="system",
        severity="warning",
        before=before,
        after={"queued": True},
        metadata={"reason": payload.reason},
        request=request,
    )
    await session.commit()
    return {"id": str(row.id), "queued": True}
