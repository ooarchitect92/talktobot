import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from northstar_api.services import kafka_topics


def metadata(replication=3):
    return [
        {
            "topic": name,
            "error_code": 0,
            "partitions": [
                {
                    "error_code": 0,
                    "leader": 1,
                    "replicas": list(range(replication)),
                    "isr": list(range(replication)),
                }
            ],
        }
        for name in kafka_topics.EVENT_TOPICS
    ]


async def test_topics_gate_creates_only_missing_topics_and_reuses_existing():
    existing = set(kafka_topics.EVENT_TOPICS[:-1])
    admin = SimpleNamespace(
        list_topics=AsyncMock(return_value=list(existing)),
        create_topics=AsyncMock(return_value=SimpleNamespace(topic_errors=[("topic", 0, None)])),
        describe_topics=AsyncMock(return_value=metadata()),
    )
    assert await kafka_topics.ensure_topics(admin, replication_factor=3) == 1
    topics = admin.create_topics.call_args.args[0]
    assert len(topics) == 1 and topics[0].name == kafka_topics.EVENT_TOPICS[-1]
    assert topics[0].replication_factor == 3
    assert topics[0].topic_configs["min.insync.replicas"] == "2"
    admin.list_topics.return_value = list(kafka_topics.EVENT_TOPICS)
    admin.create_topics.reset_mock()
    assert await kafka_topics.ensure_topics(admin, replication_factor=3) == 0
    admin.create_topics.assert_not_called()


async def test_under_replicated_topics_fail_release_gate(monkeypatch):
    monkeypatch.setattr(kafka_topics.asyncio, "sleep", AsyncMock())
    admin = SimpleNamespace(
        list_topics=AsyncMock(return_value=list(kafka_topics.EVENT_TOPICS)),
        describe_topics=AsyncMock(return_value=metadata(replication=1)),
    )
    with pytest.raises(RuntimeError, match="replication"):
        await kafka_topics.ensure_topics(admin, replication_factor=3)


async def test_broker_rejection_never_passes_release_gate():
    admin = SimpleNamespace(
        list_topics=AsyncMock(return_value=[]),
        create_topics=AsyncMock(return_value=SimpleNamespace(topic_errors=[("topic", 29, "denied")])),
    )
    with pytest.raises(RuntimeError, match="rejected"):
        await kafka_topics.ensure_topics(admin, replication_factor=3)


def test_registry_covers_worker_topics_and_versioned_event_names():
    source = Path(kafka_topics.__file__).resolve().parents[1]
    found = set()
    for path in source.rglob("*.py"):
        found.update(re.findall(r'"([a-z][a-z0-9_.-]+\.v1)"', path.read_text(encoding="utf-8")))
    found -= {"app.jobs.v1", "talktobot.website.archive.v1"}
    assert found <= set(kafka_topics.EVENT_TOPICS)
