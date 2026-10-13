from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from northstar_api.config import get_settings
from northstar_api.database import SessionFactory
from northstar_api.email_verification import EmailVerificationState
from northstar_api.models import User
from northstar_api.security import decode_token
from northstar_api.services.mfa import totp_code


async def account(client: AsyncClient):
    email = f"required-{uuid4().hex[:12]}@example.com"
    password = "Authenticator-Test-2026!"  # noqa: S105 - synthetic fixture only
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Authenticator Test",
            "email": email,
            "password": password,
            "organizationName": email.split("@")[0],
            "termsAccepted": True,
            "privacyAccepted": True,
        },
    )
    assert response.status_code == 201, response.text
    async with SessionFactory() as db:
        user = await db.scalar(select(User).where(User.email == email))
        state = await db.get(EmailVerificationState, user.id)
        state.verified_at = datetime.now(UTC)
        await db.commit()
    return email, password, response.json()


async def test_required_enrollment_cannot_access_resources_or_refresh(
    client: AsyncClient, monkeypatch, mfa_recovery_emails
):
    email, password, old_session = await account(client)
    monkeypatch.setattr(get_settings(), "mfa_required", True)
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    payload = login.json()
    assert payload["mfaEnrollmentRequired"] is True
    assert "accessToken" not in payload and "refreshToken" not in payload
    assert login.headers["cache-control"] == "no-store"
    token = payload["enrollmentToken"]
    with pytest.raises(ValueError):
        decode_token(token, "access")
    with pytest.raises(ValueError):
        decode_token(token, "refresh")
    headers = {"Authorization": f"Bearer {token}"}
    for path in ("/bootstrap", "/auth/mfa/status", "/platform-admin/website/access", "/workspace/api-keys"):
        blocked = await client.get("/api/v1" + path, headers=headers)
        assert blocked.status_code in {401, 404}, blocked.text
    old_access = await client.get(
        "/api/v1/auth/mfa/status", headers={"Authorization": "Bearer " + old_session["accessToken"]}
    )
    assert old_access.status_code == 401
    old_refresh = await client.post(
        "/api/v1/auth/refresh", json={"refreshToken": old_session["refreshToken"]}
    )
    assert old_refresh.status_code == 401
    setup = await client.post("/api/v1/auth/mfa/setup", headers=headers, json={"currentPassword": password})
    assert setup.status_code == 200, setup.text
    material = setup.json()
    assert "issuer=TalkToBot" in material["otpauthUri"]
    assert "recoveryCodes" not in material
    assert material["recoveryCodesEmailed"] is True
    assert len(mfa_recovery_emails[-1][1]) == 10
    code = totp_code(material["secret"], int(datetime.now(UTC).timestamp()) // 30)
    confirmed = await client.post("/api/v1/auth/mfa/confirm", headers=headers, json={"code": code})
    assert confirmed.status_code == 200, confirmed.text
    active = confirmed.json()
    assert decode_token(active["accessToken"], "access")["mfa"] is True
    assert decode_token(active["refreshToken"], "refresh")["mfa"] is True
    replay = await client.post("/api/v1/auth/mfa/setup", headers=headers, json={"currentPassword": password})
    assert replay.status_code == 401
    status = await client.get(
        "/api/v1/auth/mfa/status", headers={"Authorization": "Bearer " + active["accessToken"]}
    )
    assert status.json()["required"] is True
    disabled = await client.request(
        "DELETE",
        "/api/v1/auth/mfa",
        headers={"Authorization": "Bearer " + active["accessToken"]},
        json={"currentPassword": password, "recoveryCode": mfa_recovery_emails[-1][1][0]},
    )
    assert disabled.status_code == 403
    refresh = await client.post("/api/v1/auth/refresh", json={"refreshToken": active["refreshToken"]})
    assert refresh.status_code == 200
    assert decode_token(refresh.json()["accessToken"], "access")["mfa"] is True


async def test_mandatory_signup_only_issues_enrollment(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(get_settings(), "mfa_required", True)
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "name": "New Authenticator User",
            "email": f"new-{uuid4().hex[:12]}@example.com",
            "password": "Mandatory-Enrollment-2026!",
            "organizationName": "Mandatory " + uuid4().hex[:8],
            "termsAccepted": True,
            "privacyAccepted": True,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["mfaEnrollmentRequired"] is True
    assert "accessToken" not in response.json()
    assert "northstar_refresh" not in response.cookies


async def test_cancelled_enrollment_cannot_be_reused(client: AsyncClient, monkeypatch):
    email, password, _ = await account(client)
    monkeypatch.setattr(get_settings(), "mfa_required", True)
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": "Bearer " + login.json()["enrollmentToken"]}
    cancelled = await client.post("/api/v1/auth/mfa/enrollment/logout", headers=headers)
    assert cancelled.status_code == 204
    setup = await client.post("/api/v1/auth/mfa/setup", headers=headers, json={"currentPassword": password})
    assert setup.status_code == 401


def test_totp_matches_independent_rfc_vector():
    # RFC 6238 SHA-1 vector at timestamp 59; the standard eight-digit value is 94287082.
    assert totp_code("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", 1) == "287082"


def test_production_cannot_disable_mfa_policy(monkeypatch):
    settings = get_settings().model_copy(update={"app_env": "production", "mfa_required": False})
    assert settings.requires_mfa


def test_key_rotation_preserves_encrypted_authenticator_secrets(monkeypatch):
    from pydantic import SecretStr

    from northstar_api.services.mfa import (
        _application_secrets,
        _decrypt_secret,
        _encrypt_secret,
        _recovery_hash,
    )

    settings = get_settings()
    first_key = "first-encryption-key-for-authenticator-tests-2026"
    second_key = "second-encryption-key-for-authenticator-tests-2026"
    monkeypatch.setattr(settings, "mfa_encryption_key", SecretStr(first_key))
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # noqa: S105 - public RFC fixture
    user_id = uuid4()
    ciphertext = _encrypt_secret(secret)
    old_hash = _recovery_hash(user_id, "ABCD-EFGH-JKLM")
    monkeypatch.setattr(settings, "mfa_encryption_key", SecretStr(second_key))
    monkeypatch.setattr(settings, "mfa_previous_encryption_keys", [SecretStr(first_key)])
    assert _decrypt_secret(ciphertext) == secret
    assert old_hash in [_recovery_hash(user_id, "ABCD-EFGH-JKLM", key) for key in _application_secrets()]
