from uuid import uuid4

from httpx import AsyncClient

ADMIN = "/api/v1/platform-admin/website"


async def publish(client: AsyncClient, headers: dict, row: dict) -> dict:
    for action in ("review", "approve", "publish"):
        response = await client.post(
            f"{ADMIN}/resources/{row['id']}/actions",
            headers=headers,
            json={"version": row["version"], "action": action, "reason": "Guide acceptance"},
        )
        assert response.status_code == 200, response.text
        row = response.json()
    return row


async def test_guides_are_distinct_private_and_owner_managed(client: AsyncClient, auth_headers: dict):
    response = await client.get(f"{ADMIN}/starter-guides", headers=auth_headers)
    assert response.status_code == 200
    originals = response.json()
    assert len({guide["data"]["body"] for guide in originals}) == 3
    assert (await client.get(f"{ADMIN}/starter-guides")).status_code == 401
    key = "qa-guide-" + uuid4().hex
    payload = {
        "kind": "article_template",
        "key": key,
        "title": "A distinct custom guide",
        "data": {
            "excerpt": "A configurable editorial starting point",
            "body": "# Custom guide\n\nPrepare your course sources and review the resulting answers.",
        },
    }
    response = await client.post(f"{ADMIN}/resources", headers=auth_headers, json=payload)
    assert response.status_code == 201, response.text
    row = response.json()
    assert key not in {
        guide["key"] for guide in (await client.get(f"{ADMIN}/starter-guides", headers=auth_headers)).json()
    }
    row = await publish(client, auth_headers, row)
    guides = (await client.get(f"{ADMIN}/starter-guides", headers=auth_headers)).json()
    assert next(guide for guide in guides if guide["key"] == key)["data"]["body"] == payload["data"]["body"]
    manifest = (await client.get("/api/v1/website/manifest")).json()
    assert key not in {resource["key"] for resource in manifest["resources"]}
    updated = {**payload, "version": row["version"], "title": "Unpublished template changes"}
    response = await client.put(f"{ADMIN}/resources/{row['id']}", headers=auth_headers, json=updated)
    assert response.status_code == 200
    guides = (await client.get(f"{ADMIN}/starter-guides", headers=auth_headers)).json()
    assert next(guide for guide in guides if guide["key"] == key)["title"] == payload["title"]
    row = response.json()
    response = await client.post(
        f"{ADMIN}/resources/{row['id']}/actions",
        headers=auth_headers,
        json={"version": row["version"], "action": "archive", "reason": "Retire test template"},
    )
    assert response.status_code == 200
    assert key not in {
        guide["key"] for guide in (await client.get(f"{ADMIN}/starter-guides", headers=auth_headers)).json()
    }


async def test_builtin_changes_preserve_current_guide_until_publication(
    client: AsyncClient, auth_headers: dict
):
    original = (await client.get(f"{ADMIN}/starter-guides", headers=auth_headers)).json()[0]
    payload = {
        "kind": "article_template",
        "key": original["key"],
        "title": "Private knowledge guide revision",
        "data": original["data"],
    }
    response = await client.post(f"{ADMIN}/resources", headers=auth_headers, json=payload)
    assert response.status_code == 201, response.text
    row = response.json()
    guides = (await client.get(f"{ADMIN}/starter-guides", headers=auth_headers)).json()
    assert next(guide for guide in guides if guide["key"] == original["key"])["title"] == original["title"]
    row = await publish(client, auth_headers, row)
    guides = (await client.get(f"{ADMIN}/starter-guides", headers=auth_headers)).json()
    assert next(guide for guide in guides if guide["key"] == original["key"])["title"] == payload["title"]
    response = await client.post(
        f"{ADMIN}/resources/{row['id']}/actions",
        headers=auth_headers,
        json={"version": row["version"], "action": "unpublish", "reason": "Disable guide"},
    )
    assert response.status_code == 200
    assert original["key"] not in {
        guide["key"] for guide in (await client.get(f"{ADMIN}/starter-guides", headers=auth_headers)).json()
    }
