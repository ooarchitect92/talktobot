from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException, Request
from httpx import AsyncClient
from pydantic import ValidationError

from northstar_api.database import SessionFactory
from northstar_api.models import Role, User
from northstar_api.security import Principal, hash_password
from northstar_api.website import PostInput, require_editor

ADMIN = "/api/v1/platform-admin/website"
PUBLIC = "/api/v1/website"


async def test_draft_publication_conflict_and_manual_restore(client: AsyncClient, auth_headers: dict) -> None:
    payload = {
        "title": "Website acceptance article",
        "slug": f"acceptance-{uuid4().hex}",
        "body": "# Approved content\n\nA useful article for the public website.",
    }
    anonymous = await client.get(f"{ADMIN}/posts")
    assert anonymous.status_code == 401
    created = await client.post(f"{ADMIN}/posts", headers=auth_headers, json=payload)
    assert created.status_code == 201, created.text
    assert created.headers["cache-control"] == "no-store"
    post = created.json()
    assert (await client.get(f"{PUBLIC}/posts/{post['slug']}")).status_code == 404
    denied = await client.post(
        f"{ADMIN}/posts/{post['id']}/actions",
        headers=auth_headers,
        json={"version": post["version"], "action": "publish"},
    )
    assert denied.status_code == 409
    for action in ("review", "approve"):
        step = await client.post(
            f"{ADMIN}/posts/{post['id']}/actions",
            headers=auth_headers,
            json={"version": post["version"], "action": action, "reason": "Editorial acceptance"},
        )
        assert step.status_code == 200, step.text
        post = step.json()
    published = await client.post(
        f"{ADMIN}/posts/{post['id']}/actions",
        headers=auth_headers,
        json={"version": post["version"], "action": "publish"},
    )
    assert published.status_code == 200, published.text
    post = published.json()
    visible = (await client.get(f"{PUBLIC}/posts/{post['slug']}")).json()
    original_version = visible["version"]
    edited = await client.put(
        f"{ADMIN}/posts/{post['id']}",
        headers=auth_headers,
        json={**payload, "version": post["version"], "body": "Private draft: not published yet."},
    )
    assert edited.status_code == 200, edited.text
    conflict = await client.put(
        f"{ADMIN}/posts/{post['id']}", headers=auth_headers, json={**payload, "version": post["version"]}
    )
    assert conflict.status_code == 409
    visible = (await client.get(f"{PUBLIC}/posts/{post['slug']}")).json()
    assert "Private draft" not in visible["body"]
    assert visible["version"] == original_version
    post = edited.json()
    rejected = await client.post(
        f"{ADMIN}/posts/{post['id']}/actions",
        headers=auth_headers,
        json={"version": post["version"], "action": "trash"},
    )
    assert rejected.status_code == 422
    trashed = await client.post(
        f"{ADMIN}/posts/{post['id']}/actions",
        headers=auth_headers,
        json={"version": post["version"], "action": "trash", "reason": "Acceptance test"},
    )
    assert trashed.status_code == 200
    assert (await client.get(f"{PUBLIC}/posts/{post['slug']}")).status_code == 404
    restored = await client.post(
        f"{ADMIN}/posts/{post['id']}/actions",
        headers=auth_headers,
        json={"version": trashed.json()["version"], "action": "restore"},
    )
    assert restored.json()["status"] == "draft"
    assert restored.json()["body"] == "Private draft: not published yet."
    history = await client.get(f"{ADMIN}/posts/{post['id']}/revisions", headers=auth_headers)
    assert len(history.json()) == 7
    assert all(row["actor_id"] for row in history.json())
    assert (await client.delete(f"{ADMIN}/posts/{post['id']}", headers=auth_headers)).status_code == 405


async def test_an_ordinary_account_cannot_edit_global_website(client: AsyncClient) -> None:
    async with SessionFactory() as session:
        user = User(
            email=f"non-editor-{uuid4().hex}@example.com",
            name="Ordinary owner",
            password_hash=hash_password("Not-An-Editor-42!"),
        )
        session.add(user)
        await session.flush()
        principal = Principal(user_id=user.id, tenant_id=uuid4(), role=Role.OWNER, token_id=uuid4().hex)
        with pytest.raises(HTTPException) as error:
            await require_editor(
                principal,
                session,
                Request(
                    {
                        "type": "http",
                        "method": "GET",
                        "path": "/api/v1/platform-admin/website/access",
                        "headers": [],
                    }
                ),
            )
        assert error.value.status_code == 403
        await session.rollback()


async def test_enquiry_acknowledgement_is_durable_and_idempotent(
    client: AsyncClient, auth_headers: dict
) -> None:
    payload = {
        "id": str(uuid4()),
        "name": "Website visitor",
        "email": "visitor@example.com",
        "message": "Please help me explore a business assistant.",
        "consent": True,
    }
    accepted = await client.post(f"{PUBLIC}/inquiries", json=payload)
    assert accepted.status_code == 201, accepted.text
    retry = await client.post(f"{PUBLIC}/inquiries", json=payload)
    assert retry.status_code == 201
    assert accepted.json() == retry.json()
    conflict = await client.post(
        f"{PUBLIC}/inquiries", json={**payload, "message": "A different request reusing the same ID."}
    )
    assert conflict.status_code == 409
    rows = (await client.get(f"{ADMIN}/inquiries", headers=auth_headers)).json()
    assert sum(row["id"] == payload["id"] for row in rows) == 1
    denied = await client.post(f"{PUBLIC}/inquiries", json={**payload, "id": str(uuid4()), "consent": False})
    assert denied.status_code == 422
    assert (await client.get(f"{ADMIN}/inquiries")).status_code == 401


def test_cover_rejects_active_or_fake_images() -> None:
    payload = {"title": "A valid title", "slug": "valid-title", "body": "Valid article content."}
    for cover in [
        "data:image/svg+xml;base64,PHN2Zz4=",
        "https://example.com/tracker.png",
        "data:image/png;base64,bm90LWFuLWltYWdl",
    ]:
        with pytest.raises(ValidationError):
            PostInput(**payload, cover=cover)


@pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "on", "t", "T", "y", "Y"])
async def test_content_editor_cannot_export_contact_data(
    client: AsyncClient, auth_headers: dict, monkeypatch, value: str
) -> None:
    from northstar_api.config import get_settings

    monkeypatch.setattr(get_settings(), "website_editor_roles", {"owner@example.com": ["editor"]})
    response = await client.get(f"{ADMIN}/exports?include_contacts={value}", headers=auth_headers)
    assert response.status_code == 403


async def test_content_editor_cannot_publish(client: AsyncClient, auth_headers: dict, monkeypatch) -> None:
    from northstar_api.config import get_settings

    monkeypatch.setattr(get_settings(), "website_editor_roles", {"owner@example.com": ["editor"]})
    response = await client.post(
        f"{ADMIN}/posts/{uuid4()}/actions", headers=auth_headers, json={"version": 1, "action": "publish"}
    )
    assert response.status_code == 403
