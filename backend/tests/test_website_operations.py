import base64
import io
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image

ADMIN = "/api/v1/platform-admin/website"
PUBLIC = "/api/v1/website"


async def create(client: AsyncClient, headers: dict, kind: str, data: dict) -> dict:
    response = await client.post(
        f"{ADMIN}/resources",
        headers=headers,
        json={"kind": kind, "key": uuid4().hex, "title": "Acceptance resource", "data": data},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_import_validation_atomic_drafts_and_private_archive(
    client: AsyncClient, auth_headers: dict
) -> None:
    item = {
        "kind": "page",
        "key": uuid4().hex,
        "title": "Imported private page",
        "data": {
            "route": f"/import-{uuid4().hex}",
            "blocks": [{"id": "hero", "type": "hero", "title": "Imported page"}],
        },
    }
    before = (await client.get(f"{ADMIN}/overview", headers=auth_headers)).json()["resources"]
    dry_run = await client.post(f"{ADMIN}/imports", headers=auth_headers, json={"resources": [item]})
    assert dry_run.status_code == 200, dry_run.text
    assert (await client.get(f"{ADMIN}/overview", headers=auth_headers)).json()["resources"] == before
    imported = await client.post(
        f"{ADMIN}/imports",
        headers=auth_headers,
        json={
            "resources": [item],
            "action": "apply",
            "checksum": dry_run.json()["checksum"],
            "reason": "Reviewed resource import",
        },
    )
    assert imported.status_code == 200, imported.text
    assert len(imported.json()["created"]) == 1
    assert all(
        row["key"] != item["key"] for row in (await client.get(f"{PUBLIC}/manifest")).json()["resources"]
    )
    duplicate = await client.post(f"{ADMIN}/imports", headers=auth_headers, json={"resources": [item]})
    assert not duplicate.json()["can_apply"]
    assert (await client.get(f"{ADMIN}/exports")).status_code == 401
    archive = (await client.get(f"{ADMIN}/exports", headers=auth_headers)).json()
    assert len(archive["sha256"]) == 64
    assert "inquiries" not in archive["content"]
    assert (await client.get(f"{ADMIN}/quality", headers=auth_headers)).status_code == 200


@pytest.mark.parametrize("revoked_field", ["is_active", "email_verification"])
async def test_schedules_survive_restart_publish_once_and_recheck_actor(
    client: AsyncClient, auth_headers: dict, revoked_field: str
) -> None:
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    from northstar_api.database import SessionFactory
    from northstar_api.email_verification import EmailVerificationState
    from northstar_api.models import User
    from northstar_api.website import WebsitePost
    from northstar_api.website_operations import WebsiteResource
    from northstar_api.workers.website_scheduler import tick

    row = await create(
        client,
        auth_headers,
        "page",
        {
            "route": f"/scheduled-{uuid4().hex}",
            "blocks": [{"id": "h", "type": "hero", "title": "Scheduled content"}],
        },
    )
    for action in ("review", "approve"):
        row = (
            await client.post(
                f"{ADMIN}/resources/{row['id']}/actions",
                headers=auth_headers,
                json={"version": row["version"], "action": action, "reason": "Schedule acceptance"},
            )
        ).json()
    scheduled = await client.post(
        f"{ADMIN}/resources/{row['id']}/actions",
        headers=auth_headers,
        json={
            "version": row["version"],
            "action": "schedule",
            "reason": "Publish later",
            "scheduled_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "editorial_timezone": "Asia/Kolkata",
        },
    )
    assert scheduled.status_code == 200, scheduled.text
    row = scheduled.json()
    post = (
        await client.post(
            f"{ADMIN}/posts",
            headers=auth_headers,
            json={
                "title": "Scheduled article",
                "slug": f"scheduled-{uuid4().hex}",
                "body": "Approved scheduled article",
            },
        )
    ).json()
    for action in ("review", "approve", "schedule"):
        payload = {"version": post["version"], "action": action, "reason": "Approved article schedule"}
        if action == "schedule":
            payload["scheduled_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        response = await client.post(
            f"{ADMIN}/posts/{post['id']}/actions", headers=auth_headers, json=payload
        )
        assert response.status_code == 200, response.text
        post = response.json()
    async with SessionFactory() as session:
        resource = await session.get(WebsiteResource, UUID(row["id"]))
        article = await session.get(WebsitePost, UUID(post["id"]))
        resource.scheduled_at = article.scheduled_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    assert await tick() == 2
    assert await tick() == 0
    assert (await client.get(f"{PUBLIC}/posts/{post['slug']}")).status_code == 200
    current = (await client.get(f"{ADMIN}/resources", headers=auth_headers)).json()
    resource = next(r for r in current if r["id"] == row["id"])
    edited = await client.put(
        f"{ADMIN}/resources/{row['id']}",
        headers=auth_headers,
        json={
            "kind": "page",
            "key": resource["key"],
            "title": "Revoked actor draft",
            "data": resource["data"],
            "version": resource["version"],
        },
    )
    resource = edited.json()
    for action in ("review", "approve", "schedule"):
        payload = {"version": resource["version"], "action": action, "reason": "Test revocation"}
        if action == "schedule":
            payload["scheduled_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        resource = (
            await client.post(f"{ADMIN}/resources/{row['id']}/actions", headers=auth_headers, json=payload)
        ).json()
    async with SessionFactory() as session:
        resource_row = await session.get(WebsiteResource, UUID(row["id"]))
        resource_row.scheduled_at = datetime.now(UTC) - timedelta(seconds=1)
        actor = await session.get(User, resource_row.scheduled_actor_id)
        if revoked_field == "email_verification":
            verification = await session.get(EmailVerificationState, actor.id)
            if verification is None:
                session.add(EmailVerificationState(user_id=actor.id, verified_at=None))
            else:
                verification.verified_at = None
        else:
            actor.is_active = False
        await session.commit()
    try:
        assert await tick() == 0
        async with SessionFactory() as session:
            resource_row = await session.get(WebsiteResource, UUID(row["id"]))
            assert resource_row.status == "publication_failed"
            assert resource_row.published_document["title"] != "Revoked actor draft"
    finally:
        async with SessionFactory() as session:
            actor = await session.get(User, actor.id)
            if revoked_field == "email_verification":
                verification = await session.get(EmailVerificationState, actor.id)
                verification.verified_at = datetime.now(UTC)
            else:
                actor.is_active = True
            await session.commit()


async def publish(client: AsyncClient, headers: dict, row: dict) -> dict:
    for action in ("review", "approve", "publish"):
        response = await client.post(
            f"{ADMIN}/resources/{row['id']}/actions",
            headers=headers,
            json={"version": row["version"], "action": action, "reason": "Acceptance review"},
        )
        assert response.status_code == 200, response.text
        row = response.json()
    return row


async def test_resource_private_review_live_snapshot_and_conflict(
    client: AsyncClient, auth_headers: dict
) -> None:
    data = {
        "route": f"/acceptance-{uuid4().hex}",
        "blocks": [
            {"id": "hero", "type": "hero", "title": "Public headline", "body": "Useful approved content"}
        ],
    }
    row = await create(client, auth_headers, "page", data)
    assert all(
        item["id"] != row["id"] for item in (await client.get(f"{PUBLIC}/manifest")).json()["resources"]
    )
    denied = await client.post(
        f"{ADMIN}/resources/{row['id']}/actions",
        headers=auth_headers,
        json={"version": row["version"], "action": "publish", "reason": "No approval"},
    )
    assert denied.status_code == 409
    row = await publish(client, auth_headers, row)
    public_before = next(
        item
        for item in (await client.get(f"{PUBLIC}/manifest")).json()["resources"]
        if item["id"] == row["id"]
    )
    saved = await client.put(
        f"{ADMIN}/resources/{row['id']}",
        headers=auth_headers,
        json={
            "kind": "page",
            "key": row["key"],
            "title": "Private new headline",
            "data": data,
            "version": row["version"],
        },
    )
    assert saved.status_code == 200
    visible = (await client.get(f"{PUBLIC}/manifest")).json()["resources"]
    assert next(item for item in visible if item["id"] == row["id"])["title"] == "Acceptance resource"
    public_after = next(item for item in visible if item["id"] == row["id"])
    assert public_after["updated_at"] == public_before["updated_at"]
    assert public_after["status"] == "published"
    assert public_after["scheduled_at"] is None
    stale = await client.put(
        f"{ADMIN}/resources/{row['id']}",
        headers=auth_headers,
        json={
            "kind": "page",
            "key": row["key"],
            "title": "Stale overwrite",
            "data": data,
            "version": row["version"],
        },
    )
    assert stale.status_code == 409
    history = (await client.get(f"{ADMIN}/resources/{row['id']}/history", headers=auth_headers)).json()
    assert len(history) == 5
    audit = (
        await client.get(f"{ADMIN}/audit", params={"resource_id": row["id"]}, headers=auth_headers)
    ).json()["items"]
    assert all(item["actor_id"] != "system" for item in audit)
    assert (await client.get(f"{ADMIN}/audit")).status_code == 401


async def test_form_acceptance_workflow_idempotency_and_lead_stage(
    client: AsyncClient, auth_headers: dict
) -> None:
    workflow = await create(
        client,
        auth_headers,
        "workflow",
        {"trigger": "inquiry_accepted", "action": "assign", "value": "Local sales operator"},
    )
    await publish(client, auth_headers, workflow)
    form = await create(
        client,
        auth_headers,
        "form",
        {
            "fields": [
                {"key": "name", "label": "Name", "type": "text", "required": True},
                {"key": "email", "label": "Email", "type": "email", "required": True},
            ]
        },
    )
    form = await publish(client, auth_headers, form)
    payload = {
        "id": str(uuid4()),
        "answers": {"name": "Test contact", "email": "owner@example.com"},
        "consent": True,
    }
    path = f"{PUBLIC}/forms/{form['key']}/submit"
    for invalid_answers in (
        {"name": " ", "email": "owner@example.com"},
        {"name": "Test contact", "email": ""},
    ):
        assert (
            await client.post(path, json={**payload, "id": str(uuid4()), "answers": invalid_answers})
        ).status_code == 422
    first = await client.post(path, json=payload)
    assert first.status_code == 201, first.text
    assert (await client.post(path, json=payload)).json() == first.json()
    changed = await client.post(
        path, json={**payload, "answers": {**payload["answers"], "name": "Different person"}}
    )
    assert changed.status_code == 409
    assert (
        await client.post(path, json={**payload, "id": str(uuid4()), "consent": False})
    ).status_code == 422
    leads = (await client.get(f"{ADMIN}/leads", headers=auth_headers)).json()
    lead = next(r for r in leads if r["id"] == payload["id"])
    assert lead["operations"]["assignee"] == "Local sales operator"
    updated = await client.put(
        f"{ADMIN}/leads/{lead['id']}",
        headers=auth_headers,
        json={"version": lead["version"], "stage": "qualified", "reason": "Explicit operator qualification"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["operations"]["stage"] == "qualified"
    audit = (await client.get(f"{ADMIN}/audit", headers=auth_headers)).json()["items"]
    assert any(r["kind"] == "workflow" and r["action"] == "executed" for r in audit)


async def test_route_and_redirect_publication_integrity(client: AsyncClient, auth_headers: dict) -> None:
    destination = await create(
        client,
        auth_headers,
        "page",
        {"route": "/old-b", "blocks": [{"id": "h", "type": "hero", "title": "Destination"}]},
    )
    destination = await publish(client, auth_headers, destination)
    first = await create(client, auth_headers, "redirect", {"source": "/old-a", "target": "/old-b"})
    await publish(client, auth_headers, first)
    await client.post(
        f"{ADMIN}/resources/{destination['id']}/actions",
        headers=auth_headers,
        json={
            "version": destination["version"],
            "action": "unpublish",
            "reason": "Exercise redirect cycle validation",
        },
    )
    second = await create(client, auth_headers, "redirect", {"source": "/old-b", "target": "/old-a"})
    for action in ("review", "approve"):
        second = (
            await client.post(
                f"{ADMIN}/resources/{second['id']}/actions",
                headers=auth_headers,
                json={"version": second["version"], "action": action, "reason": "Review redirect"},
            )
        ).json()
    invalid = await client.post(
        f"{ADMIN}/resources/{second['id']}/actions",
        headers=auth_headers,
        json={"version": second["version"], "action": "publish", "reason": "Attempt cycle"},
    )
    assert invalid.status_code == 422
    external = await client.post(
        f"{ADMIN}/resources",
        headers=auth_headers,
        json={
            "kind": "redirect",
            "key": "external",
            "title": "Unsafe redirect",
            "data": {"source": "/safe", "target": "https://evil.example"},
        },
    )
    assert external.status_code == 422
    unsafe = await client.post(
        f"{ADMIN}/resources",
        headers=auth_headers,
        json={
            "kind": "page",
            "key": "script",
            "title": "Unsafe section",
            "data": {"route": "/unsafe", "blocks": [{"id": "bad", "type": "script"}]},
        },
    )
    assert unsafe.status_code == 422


async def test_collection_entries_and_schema_preservation(client: AsyncClient, auth_headers: dict) -> None:
    collection = await create(
        client,
        auth_headers,
        "collection",
        {"fields": [{"key": "description", "label": "Description", "type": "text", "required": True}]},
    )
    entry = await create(
        client,
        auth_headers,
        "entry",
        {"collection_key": collection["key"], "fields": {"description": "A truthful informational entry."}},
    )
    await publish(client, auth_headers, collection)
    await publish(client, auth_headers, entry)
    visible = (await client.get(f"{PUBLIC}/manifest")).json()["resources"]
    assert any(r["kind"] == "entry" for r in visible)
    current = next(
        r
        for r in (await client.get(f"{ADMIN}/resources", headers=auth_headers)).json()
        if r["id"] == collection["id"]
    )
    breaking = await client.put(
        f"{ADMIN}/resources/{current['id']}",
        headers=auth_headers,
        json={
            "kind": "collection",
            "key": current["key"],
            "version": current["version"],
            "title": current["title"],
            "data": {"fields": [{"key": "description", "type": "number"}]},
        },
    )
    assert breaking.status_code == 409
    archived = await client.post(
        f"{ADMIN}/resources/{current['id']}/actions",
        headers=auth_headers,
        json={"action": "archive", "version": current["version"], "reason": "Hide collection"},
    )
    assert archived.status_code == 200
    assert not any(r["kind"] == "entry" for r in (await client.get(f"{PUBLIC}/manifest")).json()["resources"])


async def test_media_metadata_and_private_public_boundary(
    client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from northstar_api.website_operations import object_store

    images = {}

    async def put(asset_id, data, thumbnail):
        images["image"] = data
        images["thumbnail"] = thumbnail
        return "image", "thumbnail"

    async def get(key, **kwargs):
        return images[key], {}

    monkeypatch.setattr(object_store, "put_website_image", put)
    monkeypatch.setattr(object_store, "download", get)
    original = io.BytesIO()
    Image.new("RGB", (1200, 900), "blue").save(original, format="PNG")
    payload = {
        "image": "data:image/png;base64," + base64.b64encode(original.getvalue()).decode(),
        "title": "Licensed acceptance image",
        "alt": "Blue acceptance image",
        "rights": "Generated test image; local acceptance only",
    }
    response = await client.post(f"{ADMIN}/media", headers=auth_headers, json=payload)
    assert response.status_code == 201, response.text
    asset = response.json()
    assert (await client.get(asset["url"])).status_code == 404
    with Image.open(io.BytesIO(images["thumbnail"])) as image:
        assert image.width <= 480 and image.format == "WEBP" and not image.getexif()
    page = await create(
        client,
        auth_headers,
        "page",
        {
            "route": "/licensed-image",
            "blocks": [
                {
                    "id": "image",
                    "type": "image",
                    "asset_id": asset["id"],
                    "alt": "Accessible use-specific description",
                }
            ],
        },
    )
    page = await publish(client, auth_headers, page)
    assert (await client.get(asset["url"])).status_code == 200
    await client.post(
        f"{ADMIN}/resources/{page['id']}/actions",
        headers=auth_headers,
        json={"action": "unpublish", "version": page["version"], "reason": "Hide image use"},
    )
    assert (await client.get(asset["url"])).status_code == 404
    bad = await client.post(
        f"{ADMIN}/media",
        headers=auth_headers,
        json={**payload, "image": "data:image/png;base64,PHNjcmlwdD4="},
    )
    assert bad.status_code == 422
