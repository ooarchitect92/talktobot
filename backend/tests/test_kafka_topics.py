import ast
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


async def test_dynamic_audit_topics_are_replicated_without_extra_stream_partitions():
    admin = SimpleNamespace(
        list_topics=AsyncMock(return_value=[]),
        create_topics=AsyncMock(return_value=SimpleNamespace(topic_errors=[("topic", 0, None)])),
        describe_topics=AsyncMock(return_value=metadata()),
    )
    await kafka_topics.ensure_topics(admin, replication_factor=3)
    topics = {topic.name: topic for topic in admin.create_topics.call_args.args[0]}
    assert topics["organization.profile.draft_saved.v1"].num_partitions == 1
    assert topics["organization.profile.draft_saved.v1"].replication_factor == 3
    assert topics["channel.event.received.v1"].num_partitions == 3


def test_registry_covers_worker_topics_and_versioned_event_names():
    source = Path(kafka_topics.__file__).resolve().parents[1]
    found = set()
    for path in source.rglob("*.py"):
        found.update(re.findall(r'"([a-z][a-z0-9_.-]+\.v1)"', path.read_text(encoding="utf-8")))
    found -= {"app.jobs.v1", "talktobot.website.archive.v1"}
    assert found <= set(kafka_topics.EVENT_TOPICS)


def test_registry_covers_dynamic_onboarding_workspace_and_course_events():
    root = Path(kafka_topics.__file__).resolve().parents[1]
    expected = {"workspace.WorkspaceAdministrativeChanged.v1"}

    def strings(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, ast.IfExp):
            return strings(node.body) | strings(node.orelse)
        return set()

    admin = ast.parse(
        (root / "modules/workspace/events/administrative_events.py").read_text(encoding="utf-8")
    )
    for node in admin.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_EVENT_NAMES" for target in node.targets
        ):
            expected.update(f"workspace.{name}.v1" for name in ast.literal_eval(node.value).values())
    for relative in (
        "services/onboarding.py",
        "routers/workspace_invitations.py",
        "routers/course_knowledge.py",
    ):
        for node in ast.walk(ast.parse((root / relative).read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.id if isinstance(node.func, ast.Name) else ""
            if relative.endswith("onboarding.py") and name == "_record" and len(node.args) > 2:
                expected.update(f"{action}.v1" for action in strings(node.args[2]))
            if relative.endswith("workspace_invitations.py"):
                for keyword in node.keywords:
                    if keyword.arg == "action":
                        expected.update(
                            f"{action}.v1"
                            for action in strings(keyword.value)
                            if action.startswith("workspace.member.")
                        )
            if relative.endswith("course_knowledge.py") and name == "audit" and len(node.args) > 3:
                expected.update(f"education.knowledge.{action}.v1" for action in strings(node.args[3]))
    assert expected <= set(kafka_topics.EVENT_TOPICS)
    assert len(kafka_topics.EVENT_TOPICS) == len(set(kafka_topics.EVENT_TOPICS))
