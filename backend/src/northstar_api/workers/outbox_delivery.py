"""One durable transaction per event, ordered within each tenant aggregate.

Acknowledgement loss can cause a replay: consumers must deduplicate eventId.
Quarantined events block only their own aggregate until an audited repair/replay.
"""

from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import structlog
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased

from northstar_api.config import Settings
from northstar_api.metrics import OUTBOX_DELIVERIES
from northstar_api.models import OutboxEvent

logger = structlog.get_logger(__name__)


class Producer(Protocol):
    async def send_and_wait(self, topic: str, value: dict[str, Any], *, key: str) -> Any: ...


def next_event(now: datetime) -> Any:
    earlier = aliased(OutboxEvent)
    predecessor = exists(
        select(earlier.id).where(
            earlier.published_at.is_(None),
            earlier.tenant_id == OutboxEvent.tenant_id,
            earlier.aggregate_type == OutboxEvent.aggregate_type,
            earlier.aggregate_id == OutboxEvent.aggregate_id,
            or_(
                earlier.occurred_at < OutboxEvent.occurred_at,
                and_(earlier.occurred_at == OutboxEvent.occurred_at, earlier.id < OutboxEvent.id),
            ),
        )
    )
    return (
        select(OutboxEvent)
        .where(
            OutboxEvent.published_at.is_(None),
            OutboxEvent.dead_lettered_at.is_(None),
            or_(OutboxEvent.next_attempt_at.is_(None), OutboxEvent.next_attempt_at <= now),
            ~predecessor,
        )
        .order_by(OutboxEvent.occurred_at, OutboxEvent.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )


async def publish_one(
    factory: async_sessionmaker[AsyncSession], producer: Producer, settings: Settings
) -> bool:
    async with factory() as session:
        event = await session.scalar(next_event(datetime.now(UTC)))
        if event is None:
            return False
        envelope = {
            "eventId": str(event.id),
            "eventType": event.event_type,
            "schemaVersion": 1,
            "tenantId": str(event.tenant_id),
            "aggregateType": event.aggregate_type,
            "aggregateId": event.aggregate_id,
            "occurredAt": event.occurred_at.isoformat(),
            "payload": event.payload,
        }
        try:
            await asyncio.wait_for(
                producer.send_and_wait(event.event_type, envelope, key=event.aggregate_id),
                timeout=settings.outbox_publish_timeout_seconds,
            )
        except Exception as exc:
            now = datetime.now(UTC)
            event.attempts += 1
            event.last_error = type(exc).__name__[:500]
            if event.attempts >= settings.outbox_max_attempts:
                event.dead_lettered_at = now
                event.next_attempt_at = None
                result = "quarantined"
            else:
                ceiling = min(
                    settings.outbox_retry_max_seconds,
                    settings.outbox_retry_base_seconds * 2 ** min(event.attempts - 1, 20),
                )
                jitter = (1 + secrets.randbelow(1001) / 1000) / 2
                event.next_attempt_at = now + timedelta(seconds=ceiling * jitter)
                result = "retry"
            logger.warning(
                "outbox_publish_failed",
                event_id=str(event.id),
                attempts=event.attempts,
                result=result,
                error=type(exc).__name__,
            )
        else:
            event.published_at = datetime.now(UTC)
            event.next_attempt_at = None
            event.last_error = None
            result = "published"
        # A process crash before this commit replays the SAME eventId, never a new event.
        await session.commit()
        OUTBOX_DELIVERIES.labels(result=result).inc()
        return True
