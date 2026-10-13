"""Create required event topics before workers start; never delete existing topics."""

from __future__ import annotations

import asyncio
from typing import Any

from aiokafka.admin import AIOKafkaAdminClient, NewTopic  # type: ignore[import-untyped]

from northstar_api.config import get_settings
from northstar_api.services.kafka_transport import kafka_transport_options

DYNAMIC_AUDIT_TOPICS = (
    "education.knowledge.academic-review.updated.v1",
    "education.knowledge.access.revoked.v1",
    "education.knowledge.access.sync_applied.v1",
    "education.knowledge.access.sync_revoke_applied.v1",
    "education.knowledge.access.synced.v1",
    "education.knowledge.access.updated.v1",
    "education.knowledge.artifact.approved.v1",
    "education.knowledge.artifact.generated.v1",
    "education.knowledge.assignment.withdrawn.v1",
    "education.knowledge.faq.approved.v1",
    "education.knowledge.faq.created.v1",
    "education.knowledge.faq.revised.v1",
    "education.knowledge.faq.withdrawn.v1",
    "education.knowledge.index.requested.v1",
    "education.knowledge.mapping.approved.v1",
    "education.knowledge.mapping.revised.v1",
    "education.knowledge.mapping.saved.v1",
    "education.knowledge.release.prepared.v1",
    "education.knowledge.release.published.v1",
    "education.knowledge.snapshot.prepared.v1",
    "education.knowledge.source.withdrawn.v1",
    "education.knowledge.test_conversation.started.v1",
    "education.knowledge.upload.created.v1",
    "organization.branding_choice.changed.v1",
    "organization.profile.completed.v1",
    "organization.profile.draft_saved.v1",
    "workspace.BrandPublished.v1",
    "workspace.BrandRolledBack.v1",
    "workspace.BrandUpdated.v1",
    "workspace.CustomDomainActivated.v1",
    "workspace.CustomDomainCreated.v1",
    "workspace.CustomDomainDisabled.v1",
    "workspace.CustomDomainVerified.v1",
    "workspace.WorkspaceAdministrativeChanged.v1",
    "workspace.WorkspaceApiKeyCreated.v1",
    "workspace.WorkspaceApiKeyRevoked.v1",
    "workspace.WorkspaceDeveloperSettingsUpdated.v1",
    "workspace.WorkspaceMemberInvited.v1",
    "workspace.WorkspaceMemberReactivated.v1",
    "workspace.WorkspaceMemberRoleChanged.v1",
    "workspace.WorkspaceMemberSuspended.v1",
    "workspace.WorkspaceNotificationsUpdated.v1",
    "workspace.WorkspaceRoleUpdated.v1",
    "workspace.WorkspaceSecurityUpdated.v1",
    "workspace.WorkspaceTeamsUpdated.v1",
    "workspace.WorkspaceUpdated.v1",
    "workspace.member.invitation.resent.v1",
    "workspace.member.invitation.revoked.v1",
    "workspace.member.invited.v1",
    "workspace.member.joined.v1",
    "workspace.member.removed.v1",
    "workspace.member.updated.v1",
)


EVENT_TOPICS = (
    "agent.channel.changed.v1",
    "agent.created.v1",
    "agent.deleted.v1",
    "agent.duplicated.v1",
    "agent.purpose.changed.v1",
    "agent.updated.v1",
    "channel.event.processed.v1",
    "channel.event.received.v1",
    "chat.message.created.v1",
    "chat.response.completed.v1",
    "conversation.reopened.v1",
    "conversation.resolved.v1",
    "conversation.state.changed.v1",
    "crm.connection.backfill.requested.v1",
    "crm.webhook.received.v1",
    "education.access.authorized.v1",
    "education.access.denied.v1",
    "education.access_recovery.completed.v1",
    "education.access_recovery.started.v1",
    "education.access_request.approved.v1",
    "education.access_request.created.v1",
    "education.access_request.denied.v1",
    "education.batch.archived.v1",
    "education.batch.created.v1",
    "education.batch.updated.v1",
    "education.conversation.resolution.context_missing.v1",
    "education.conversation.resolved.v1",
    "education.course.agent_reassigned.v1",
    "education.course.archived.v1",
    "education.course.created.v1",
    "education.course.deleted.v1",
    "education.course.updated.v1",
    "education.curriculum.created.v1",
    "education.enrollment.automated.v1",
    "education.enrollment.created.v1",
    "education.enrollment.revoked.v1",
    "education.enrollment.status_changed.v1",
    "education.enrollment.updated.v1",
    "education.knowledge.scope.updated.v1",
    "education.student.activity.recorded.v1",
    "education.student.archived.v1",
    "education.student.created.v1",
    "education.student.deleted.v1",
    "education.student.telegram.updated.v1",
    "education.student.updated.v1",
    "education.student.whatsapp.updated.v1",
    "education.student_identity.created.v1",
    "education.student_identity.revoked.v1",
    "education.student_identity.updated.v1",
    "education.student_identity.verified.v1",
    "education.students.imported.v1",
    "feedback.recorded.v1",
    "help.support_request.created.v1",
    "integration.connection.changed.v1",
    "knowledge.fact.changed.v1",
    "knowledge.source.created.v1",
    "knowledge.source.deleted.v1",
    "knowledge.source.ingested.v1",
    "lead.captured.v1",
    "lead.created.from_conversation.v1",
    "lead.created.v1",
    "lead.crm.acceptance_test.started.v1",
    "lead.crm.delivery.acknowledged.v1",
    "lead.crm.delivery.created.v1",
    "lead.crm.delivery.failed.v1",
    "lead.crm.delivery.recovered.v1",
    "lead.crm.delivery.suppressed.v1",
    "lead.crm.delivery.verified.v1",
    "lead.crm.inbound.applied.v1",
    "lead.crm.inbound.ignored.v1",
    "lead.crm.retry.requested.v1",
    "lead.crm.sync.requested.v1",
    "lead.crm.verification.failed.v1",
    "lead.crm.verification.unsupported.v1",
    "lead.layout.updated.v1",
    "lead.profile.created.v1",
    "lead.qualified.v1",
    "lead.status.changed.v1",
    "lead.updated.v1",
    "organization.provisioned.v1",
    "organization.session.selected.v1",
    "platform.runtime.change.approved.v1",
    "starter_content.cloned.v1",
    "workspace.branding.updated.v1",
    "workspace.conversation.assignment.cleared.v1",
    "workspace.conversation.assignment.updated.v1",
    "workspace.security.updated.v1",
) + DYNAMIC_AUDIT_TOPICS


async def ensure_topics(admin: Any, *, replication_factor: int) -> int:
    existing = set(await admin.list_topics())
    missing = sorted(set(EVENT_TOPICS) - existing)
    if missing:
        response = await admin.create_topics(
            [
                NewTopic(
                    name,
                    num_partitions=1 if name in DYNAMIC_AUDIT_TOPICS else 3,
                    replication_factor=replication_factor,
                    topic_configs={
                        "min.insync.replicas": str(2 if replication_factor > 1 else 1),
                        "retention.ms": "604800000",
                    },
                )
                for name in missing
            ],
            timeout_ms=30000,
        )
        if any(item[1] not in {0, 36} for item in response.topic_errors):
            raise RuntimeError("Kafka rejected event topic creation")
    for attempt in range(30):
        metadata = await admin.describe_topics(list(EVENT_TOPICS))
        found = {
            item["topic"]
            for item in metadata
            if item.get("error_code", 0) == 0
            and item.get("partitions")
            and all(
                partition.get("error_code", 0) == 0
                and partition.get("leader", -1) >= 0
                and len(partition.get("replicas", [])) >= replication_factor
                and len(partition.get("isr", [])) >= (2 if replication_factor > 1 else 1)
                for partition in item["partitions"]
            )
        }
        if set(EVENT_TOPICS) <= found:
            return len(missing)
        if attempt < 29:
            await asyncio.sleep(1)
    raise RuntimeError("Required Kafka topics are unavailable or lack the required replication")


async def bootstrap() -> None:
    settings = get_settings()
    if not settings.kafka_enabled:
        raise RuntimeError("Kafka must be enabled for event workers")
    admin = AIOKafkaAdminClient(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id="talktobot-release-topics",
        **kafka_transport_options(),
    )
    try:
        await admin.start()
        created = await ensure_topics(
            admin, replication_factor=3 if settings.app_env in {"staging", "production"} else 1
        )
        print(f"Kafka release gate passed: {len(EVENT_TOPICS)} topics verified, {created} created.")
    finally:
        await admin.close()


if __name__ == "__main__":
    asyncio.run(bootstrap())
