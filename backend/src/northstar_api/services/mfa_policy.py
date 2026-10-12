"""Mandatory MFA policy and purpose-bound enrollment credentials."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from northstar_api.auth_session_schemas import AuthMFAEnrollmentOut
from northstar_api.config import get_settings
from northstar_api.database import get_session
from northstar_api.dependencies import authenticate_access_token, bearer
from northstar_api.models import Role, TenantMembership, User
from northstar_api.security import Principal, _token, decode_token
from northstar_api.services.password_reset import credential_version
from northstar_api.services.rate_limit import SessionStoreUnavailable, redis_services


def enrollment_response(
    user_id: UUID, tenant_id: UUID, role: Role, version: int, response: Response
) -> AuthMFAEnrollmentOut:
    token, expiry = _token(
        str(user_id),
        "mfa_enrollment",
        timedelta(minutes=5),
        {"tid": str(tenant_id), "role": role.value, "cv": version},
        get_settings(),
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.delete_cookie("northstar_refresh", path=f"{get_settings().app_api_prefix.rstrip('/')}/auth")
    return AuthMFAEnrollmentOut(enrollment_token=token, expires_at=expiry)


def require_verified_mfa(user: User, claims: dict[str, Any]) -> None:
    if get_settings().requires_mfa and (not user.mfa_enabled or claims.get("mfa") is not True):
        raise HTTPException(status_code=401, detail="Authenticator sign-in required; sign in again")


async def enrollment_or_access(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")
    raw = credentials.credentials
    try:
        claims = decode_token(raw, "mfa_enrollment")
    except ValueError:
        principal = await authenticate_access_token(raw, session, request=request)
    else:
        try:
            if await redis_services.was_consumed(f"enrollment:{claims['jti']}"):
                raise HTTPException(status_code=401, detail="Enrollment was cancelled; sign in again")
        except SessionStoreUnavailable:
            raise HTTPException(status_code=503, detail="Session service unavailable") from None
        try:
            user_id, tenant_id = UUID(claims["sub"]), UUID(claims["tid"])
            role = Role(claims["role"])
            user = await session.get(User, user_id)
            member = await session.scalar(
                select(TenantMembership).where(
                    TenantMembership.user_id == user_id, TenantMembership.tenant_id == tenant_id
                )
            )
            if (
                user is None
                or not user.is_active
                or user.mfa_enabled
                or member is None
                or member.role != role
                or int(claims.get("cv", 0)) != await credential_version(session, user_id)
            ):
                raise ValueError("Enrollment is no longer valid")
        except (ValueError, KeyError, TypeError):
            raise HTTPException(
                status_code=401, detail="Invalid or expired enrollment; sign in again"
            ) from None
        principal = Principal(user_id=user_id, tenant_id=tenant_id, role=role, token_id=claims["jti"])
    rate = await redis_services.check_rate_limit(
        f"mfa:enrollment:{principal.user_id}", 12, 300, scope="mfa_enrollment"
    )
    if not rate.allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many setup attempts. Try again later.",
            headers={"Retry-After": str(rate.retry_after)},
        )
    return principal


EnrollmentPrincipal = Annotated[Principal, Depends(enrollment_or_access)]
