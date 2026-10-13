from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select

from northstar_api.database import SessionFactory
from northstar_api.lead_crm.audit_models import IntegrationAuditEvent
from northstar_api.models import OutboxEvent
from northstar_api.routers import outbox_operations
from northstar_api.security import decode_token
from northstar_api.services.mfa import MFAError


@pytest.fixture
async def retained_event(client, session_payload):
    row = OutboxEvent(
        id=uuid4(),
        tenant_id=UUID(decode_token(session_payload["accessToken"], "access")["tid"]),
        aggregate_type="qualification",
        aggregate_id=str(uuid4()),
        event_type="test.v1",
        payload={"privateValue": "must-not-leak"},
        attempts=12,
        dead_lettered_at=datetime.now(UTC),
        last_error="TimeoutError",
    )
    async with SessionFactory() as session:
        session.add(row)
        await session.commit()
    yield row
    async with SessionFactory() as session:
        await session.execute(delete(OutboxEvent).where(OutboxEvent.id == row.id))
        await session.commit()


def enable(monkeypatch, session_payload):
    monkeypatch.setenv("PLATFORM_ADMIN_EMAILS", session_payload["user"]["email"])
    monkeypatch.setattr(
        outbox_operations.redis_services,
        "check_rate_limit",
        AsyncMock(return_value=SimpleNamespace(allowed=True)),
    )


async def test_outbox_metadata_is_platform_protected_and_never_exposes_payload(
    client, auth_headers, session_payload, retained_event, monkeypatch
):
    path = f"/api/v1/platform-admin/outbox?tenant_id={retained_event.tenant_id}"
    assert (await client.get(path, headers=auth_headers)).status_code == 403
    enable(monkeypatch, session_payload)
    response = await client.get(path, headers=auth_headers)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert "must-not-leak" not in response.text and "privateValue" not in response.text


async def test_failed_step_up_cannot_release_a_quarantined_event(
    client, auth_headers, session_payload, retained_event, monkeypatch
):
    enable(monkeypatch, session_payload)
    monkeypatch.setattr(
        outbox_operations, "consume_mfa_factor", AsyncMock(side_effect=MFAError("Invalid factor"))
    )
    response = await client.post(
        f"/api/v1/platform-admin/outbox/{retained_event.id}/retry",
        headers=auth_headers,
        json={
            "tenantId": str(retained_event.tenant_id),
            "expectedAttempts": 12,
            "reason": "Owned acceptance step-up test",
            "currentPassword": "Correct-Horse-Test-Password-42!",
            "code": "123456",
        },
    )
    assert response.status_code == 401
    async with SessionFactory() as session:
        row = await session.get(OutboxEvent, retained_event.id)
        assert row.dead_lettered_at and row.attempts == 12


async def test_retry_preserves_event_identity_audits_actor_and_rejects_repetition(
    client, auth_headers, session_payload, retained_event, monkeypatch
):
    enable(monkeypatch, session_payload)
    factor = AsyncMock()
    monkeypatch.setattr(outbox_operations, "consume_mfa_factor", factor)
    body = {
        "tenantId": str(retained_event.tenant_id),
        "expectedAttempts": 12,
        "reason": "Repair verified by owned acceptance",
        "currentPassword": "Correct-Horse-Test-Password-42!",
        "code": "123456",
    }
    path = f"/api/v1/platform-admin/outbox/{retained_event.id}/retry"
    response = await client.post(path, headers=auth_headers, json=body)
    assert response.status_code == 200 and response.json()["id"] == str(retained_event.id)
    factor.assert_awaited_once()
    assert (await client.post(path, headers=auth_headers, json=body)).status_code == 409
    async with SessionFactory() as session:
        row = await session.get(OutboxEvent, retained_event.id)
        assert row.next_attempt_at and not row.dead_lettered_at and row.attempts == 0
        evidence = await session.scalar(
            select(IntegrationAuditEvent).where(
                IntegrationAuditEvent.action == "platform.outbox.retry",
                IntegrationAuditEvent.entity_id == str(row.id),
            )
        )
        assert evidence and evidence.actor_user_id == UUID(session_payload["user"]["id"])
        assert "currentPassword" not in evidence.metadata_json
