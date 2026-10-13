from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from northstar_api.config import get_settings
from northstar_api.database import Base
from northstar_api.models import OutboxEvent, Tenant
from northstar_api.workers.outbox_delivery import publish_one

pytestmark = pytest.mark.usefixtures("client")


@pytest.fixture
async def store(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'outbox.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    tenant = uuid4()
    async with factory() as session:
        session.add(Tenant(id=tenant, name="Owned outbox test", slug=str(tenant)))
        await session.commit()
    yield factory, tenant
    await engine.dispose()


class RecordingProducer:
    def __init__(self, *, fail: str | None = None, hang: bool = False):
        self.fail = fail
        self.hang = hang
        self.events: list[dict[str, Any]] = []

    async def send_and_wait(self, topic: str, value: dict[str, Any], *, key: str):
        if topic == self.fail:
            if self.hang:
                await asyncio.sleep(60)
            raise RuntimeError("Synthetic delivery failure")
        self.events.append(value)


async def seed(factory, tenant, specs):
    now = datetime.now(UTC) - timedelta(minutes=1)
    rows = [
        OutboxEvent(
            id=uuid4(),
            tenant_id=tenant,
            aggregate_type="test",
            aggregate_id=aggregate,
            event_type=topic,
            payload={"synthetic": True},
            occurred_at=now + timedelta(seconds=i),
        )
        for i, (aggregate, topic) in enumerate(specs)
    ]
    async with factory() as session:
        session.add_all(rows)
        await session.commit()
    return rows


async def test_failed_stream_does_not_block_an_unrelated_aggregate(store):
    factory, tenant = store
    rows = await seed(factory, tenant, [("a", "fail"), ("a", "good"), ("b", "good")])
    producer = RecordingProducer(fail="fail")
    settings = get_settings()
    assert await publish_one(factory, producer, settings)
    assert await publish_one(factory, producer, settings)
    assert [e["eventId"] for e in producer.events] == [str(rows[2].id)]
    assert not await publish_one(factory, producer, settings)
    async with factory() as session:
        failed = await session.get(OutboxEvent, rows[0].id)
        assert failed.attempts == 1 and failed.next_attempt_at and not failed.published_at
        assert failed.last_error == "RuntimeError"
        assert not (await session.get(OutboxEvent, rows[1].id)).published_at


async def test_stalled_delivery_is_bounded_and_quarantined_without_dropping_order(store):
    factory, tenant = store
    rows = await seed(factory, tenant, [("a", "fail"), ("a", "good"), ("b", "good")])
    producer = RecordingProducer(fail="fail", hang=True)
    settings = get_settings().model_copy(
        update={"outbox_publish_timeout_seconds": 0.1, "outbox_max_attempts": 1}
    )
    assert await asyncio.wait_for(publish_one(factory, producer, settings), timeout=1)
    assert await publish_one(factory, producer, settings)
    assert not await publish_one(factory, producer, settings)
    async with factory() as session:
        failed = await session.get(OutboxEvent, rows[0].id)
        assert failed.dead_lettered_at and failed.last_error == "TimeoutError"
        assert not failed.published_at
        assert not (await session.get(OutboxEvent, rows[1].id)).published_at


async def test_aggregate_identity_is_scoped_to_tenant(store):
    factory, tenant = store
    other = uuid4()
    async with factory() as session:
        session.add(Tenant(id=other, name="Other owned test", slug=str(other)))
        await session.commit()
    await seed(factory, tenant, [("same-id", "fail")])
    rows = await seed(factory, other, [("same-id", "good")])
    producer = RecordingProducer(fail="fail")
    for _ in range(2):
        assert await publish_one(factory, producer, get_settings())
    assert [e["eventId"] for e in producer.events] == [str(rows[0].id)]


async def test_successful_delivery_is_not_selected_twice_and_preserves_stream_order(store):
    factory, tenant = store
    rows = await seed(factory, tenant, [("a", "one"), ("a", "two")])
    producer = RecordingProducer()
    for _ in range(2):
        assert await publish_one(factory, producer, get_settings())
    assert not await publish_one(factory, producer, get_settings())
    assert [e["eventId"] for e in producer.events] == [str(row.id) for row in rows]
    async with factory() as session:
        assert all(row.published_at for row in (await session.scalars(select(OutboxEvent))).all())


async def test_crash_after_broker_ack_replays_the_original_event_id(store):
    factory, tenant = store
    rows = await seed(factory, tenant, [("a", "good")])
    producer = RecordingProducer()

    class CrashedSession(AsyncSession):
        async def commit(self):
            raise RuntimeError("Synthetic crash after broker acknowledgement")

    crashed_factory = async_sessionmaker(factory.kw["bind"], class_=CrashedSession, expire_on_commit=False)
    with pytest.raises(RuntimeError, match="Synthetic crash"):
        await publish_one(crashed_factory, producer, get_settings())
    assert await publish_one(factory, producer, get_settings())
    assert [event["eventId"] for event in producer.events] == [str(rows[0].id), str(rows[0].id)]
    assert producer.events[0] == producer.events[1]
