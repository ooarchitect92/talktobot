from __future__ import annotations

import hashlib
import html
import json
import secrets
from datetime import UTC, datetime
from typing import Annotated, Any
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from northstar_api.config import get_settings
from northstar_api.database import get_session, set_tenant_context
from northstar_api.dependencies import AdminPrincipal, _custom_role_context
from northstar_api.lead_crm.audit import record_audit_event
from northstar_api.lead_crm.connectors import CRMConnectionContext, CRMError, crm_registry
from northstar_api.lead_crm.credentials import CredentialStoreError, credential_store
from northstar_api.lead_crm.crm_provisioning import provision_connection
from northstar_api.lead_crm.domain import CRMConnectionStatus, CRMProvider
from northstar_api.lead_crm.models import CRMConnection
from northstar_api.lead_crm.oauth import OAuthResponseMode, OAuthState, OAuthStateError, oauth_state_store
from northstar_api.lead_crm.workspace_scope import WorkspaceCRMConnection
from northstar_api.models import TenantMembership, User, Workspace, WorkspaceMembership, WorkspaceStatus
from northstar_api.modules.workspace.member_state import is_member_suspended
from northstar_api.security import TENANT_ROLE_PERMISSIONS, WORKSPACE_ROLE_PERMISSIONS, Principal
from northstar_api.services.email_verification import email_is_verified
from northstar_api.services.entitlements import EntitlementError, require_feature
from northstar_api.services.password_reset import credential_version

router = APIRouter(prefix="/crm", tags=["crm-oauth"])
DB = Annotated[AsyncSession, Depends(get_session)]


def _decrypt_credentials(connection: CRMConnection) -> dict[str, Any]:
    if not connection.credentials_encrypted:
        return {}
    try:
        return credential_store.decrypt(connection.credentials_encrypted)
    except CredentialStoreError as exc:
        raise HTTPException(status_code=409, detail="CRM credentials require reconnection") from exc


def _redirect_uri(request: Request, connection: CRMConnection) -> str:
    configured = str((connection.configuration_json or {}).get("oauthRedirectUri") or "").strip()
    if configured:
        if request.url.scheme == "https" and not configured.startswith("https://"):
            raise HTTPException(status_code=400, detail="OAuth redirect URI must use HTTPS")
        return configured

    settings = get_settings()
    public_base = str(settings.crm_oauth_public_base_url or "").strip().rstrip("/")
    if public_base:
        return f"{public_base}{settings.app_api_prefix}/crm/oauth/{connection.provider}/callback"
    return str(request.url_for("crm_oauth_callback", provider=connection.provider))


def _safe_origin(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _frontend_origin(request: Request) -> str:
    settings = get_settings()
    configured = _safe_origin(settings.crm_oauth_frontend_origin)
    if configured:
        return configured
    for candidate in settings.app_cors_origins:
        origin = _safe_origin(candidate)
        if origin:
            return origin
    host = request.headers.get("host") or request.url.hostname or "localhost"
    return f"{request.url.scheme}://{host}"


def _popup_response(
    request: Request,
    *,
    payload: dict[str, Any],
    success: bool,
) -> HTMLResponse:
    origin = _frontend_origin(request)
    result = {
        "type": "northstar:crm-oauth",
        "success": success,
        **payload,
    }
    serialized_payload = json.dumps(result, separators=(",", ":"), default=str).replace("<", "\\u003c")
    serialized_origin = json.dumps(origin)
    nonce = secrets.token_urlsafe(18)
    return_url = html.escape(f"{origin}/integrations", quote=True)
    title = "CRM connected" if success else "CRM connection needs attention"
    message = (
        "Authorization and automatic CRM setup completed."
        if success
        else str(payload.get("message") or "The CRM authorization could not be completed.")
    )
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html.escape(title)}</title>
  <style nonce="{nonce}">
    :root {{ color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: #f5f7fb; color: #172033; }}
    main {{ width: min(520px, calc(100vw - 48px)); padding: 32px; border-radius: 20px; background: white; box-shadow: 0 20px 70px rgba(25, 40, 80, .16); }}
    h1 {{ margin: 0 0 10px; font-size: 1.45rem; }} p {{ line-height: 1.55; color: #526079; }}
    a {{ display: inline-block; margin-top: 12px; color: #146cf6; font-weight: 700; text-decoration: none; }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(message)}</p>
    <a href="{return_url}">Return to Integrations</a>
  </main>
  <script nonce="{nonce}">
    const payload = {serialized_payload};
    const targetOrigin = {serialized_origin};
    if (window.opener && !window.opener.closed) {{
      window.opener.postMessage(payload, targetOrigin);
      window.setTimeout(() => window.close(), 250);
    }}
  </script>
</body>
</html>"""
    response = HTMLResponse(document, status_code=200)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; "
        f"script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )
    return response


async def _start_oauth(
    connection_id: UUID,
    request: Request,
    principal: AdminPrincipal,
    session: AsyncSession,
    *,
    response_mode: OAuthResponseMode | None = None,
) -> dict[str, Any]:
    connection = await session.scalar(
        select(CRMConnection)
        .join(WorkspaceCRMConnection, WorkspaceCRMConnection.connection_id == CRMConnection.id)
        .where(
            CRMConnection.id == connection_id,
            CRMConnection.tenant_id == principal.tenant_id,
            WorkspaceCRMConnection.tenant_id == principal.tenant_id,
            WorkspaceCRMConnection.workspace_id == principal.workspace_id,
        )
    )
    if not connection:
        raise HTTPException(status_code=404, detail="CRM connection not found in this workspace")
    try:
        provider = CRMProvider(connection.provider)
        connector = crm_registry.get(provider)
    except (ValueError, CRMError) as exc:
        raise HTTPException(status_code=409, detail="CRM connector is unavailable") from exc
    if not connector.capabilities.oauth:
        raise HTTPException(status_code=400, detail="This CRM connection does not use OAuth")

    credentials = _decrypt_credentials(connection)
    redirect_uri = _redirect_uri(request, connection)
    mode: OAuthResponseMode = response_mode or (
        "popup" if bool((connection.configuration_json or {}).get("managedOAuth")) else "json"
    )
    try:
        state = await oauth_state_store.create(
            tenant_id=principal.tenant_id,
            workspace_id=principal.workspace_id,
            connection_id=connection.id,
            user_id=principal.user_id,
            provider=provider.value,
            redirect_uri=redirect_uri,
            response_mode=mode,
            credential_version=await credential_version(session, principal.user_id),
        )
        context = CRMConnectionContext(
            tenant_id=principal.tenant_id,
            connection_id=connection.id,
            provider=provider,
            configuration=connection.configuration_json,
            credentials=credentials,
        )
        code_challenge = (
            state.code_challenge if bool(connection.configuration_json.get("pkce", False)) else None
        )
        authorization_url = connector.build_authorization_url(
            context,
            redirect_uri=redirect_uri,
            state=state.state,
            code_challenge=code_challenge,
        )
    except OAuthStateError as exc:
        raise HTTPException(status_code=503, detail="OAuth state service is unavailable") from exc
    except CRMError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    connection.status = CRMConnectionStatus.CONNECTING.value
    connection.last_error = None
    connection.configuration_json = {
        **dict(connection.configuration_json or {}),
        "oauthAttemptId": hashlib.sha256(state.state.encode()).hexdigest(),
    }
    await session.commit()
    return {
        "authorizationUrl": authorization_url,
        "expiresIn": oauth_state_store.ttl_seconds,
        "connectionId": str(connection.id),
        "provider": provider.value,
        "workspaceId": str(principal.workspace_id),
        "responseMode": mode,
    }


@router.post("/connections/{connection_id}/oauth/start")
async def start_crm_oauth(
    connection_id: UUID,
    request: Request,
    principal: AdminPrincipal,
    session: DB,
) -> dict[str, Any]:
    return await _start_oauth(connection_id, request, principal, session)


@router.post("/connections/{connection_id}/reconnect")
async def reconnect_crm(
    connection_id: UUID,
    request: Request,
    principal: AdminPrincipal,
    session: DB,
) -> dict[str, Any]:
    return await _start_oauth(connection_id, request, principal, session)


async def _callback_connection(
    session: AsyncSession,
    *,
    saved: OAuthState,
    provider: str,
) -> tuple[CRMConnection, UUID]:
    # OAuth state grants only a short-lived callback capability. Current account
    # and workspace permissions must still authorize connecting a CRM.
    if saved.workspace_id is None:
        raise HTTPException(403, "An active workspace is required for authorization")
    workspace = await session.get(Workspace, saved.workspace_id)
    user = await session.get(User, saved.user_id)
    membership = await session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == saved.workspace_id,
            WorkspaceMembership.tenant_id == saved.tenant_id,
            WorkspaceMembership.user_id == saved.user_id,
        )
    )
    tenant_member = await session.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == saved.tenant_id,
            TenantMembership.user_id == saved.user_id,
        )
    )
    if (
        workspace is None
        or workspace.tenant_id != saved.tenant_id
        or workspace.status != WorkspaceStatus.ACTIVE
        or user is None
        or not user.is_active
        or membership is None
        or tenant_member is None
        or is_member_suspended(workspace.settings_json, saved.user_id)
    ):
        raise HTTPException(403, "Workspace access changed; start authorization again")
    custom, _, _, _ = _custom_role_context(workspace, saved.user_id)
    principal = Principal(
        user_id=saved.user_id,
        tenant_id=saved.tenant_id,
        role=tenant_member.role,
        token_id=str(saved.connection_id),
        workspace_id=saved.workspace_id,
        workspace_role=membership.role,
        permissions=TENANT_ROLE_PERMISSIONS[tenant_member.role]
        | WORKSPACE_ROLE_PERMISSIONS[membership.role]
        | custom,
    )
    if not principal.can("crm.manage") or not await email_is_verified(session, saved.user_id):
        raise HTTPException(403, "CRM permissions changed; start authorization again")
    if get_settings().requires_mfa and (not user.mfa_enabled or saved.credential_version is None):
        raise HTTPException(403, "Authenticator sign-in is required; start authorization again")
    if saved.credential_version is not None and saved.credential_version != await credential_version(
        session, saved.user_id
    ):
        raise HTTPException(403, "Account security changed; start authorization again")
    try:
        await require_feature(session, tenant_id=saved.tenant_id, feature="crm")
    except EntitlementError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    conditions = [
        CRMConnection.id == saved.connection_id,
        CRMConnection.tenant_id == saved.tenant_id,
        CRMConnection.provider == provider,
        CRMConnection.status != CRMConnectionStatus.DISABLED.value,
        WorkspaceCRMConnection.tenant_id == saved.tenant_id,
    ]
    if saved.workspace_id is not None:
        conditions.append(WorkspaceCRMConnection.workspace_id == saved.workspace_id)
    row = (
        await session.execute(
            select(CRMConnection, WorkspaceCRMConnection.workspace_id)
            .join(WorkspaceCRMConnection, WorkspaceCRMConnection.connection_id == CRMConnection.id)
            .where(*conditions)
            .order_by(WorkspaceCRMConnection.created_at)
            .limit(1)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="CRM connection no longer exists")
    attempt = (row[0].configuration_json or {}).get("oauthAttemptId")
    if attempt and attempt != hashlib.sha256(saved.state.encode()).hexdigest():
        raise HTTPException(400, "Authorization was restarted; use the newest authorization window")
    return row[0], row[1]


def _callback_failure(
    request: Request,
    saved: OAuthState,
    *,
    detail: str,
    payload: dict[str, Any],
    status_code: int,
) -> dict[str, Any] | HTMLResponse:
    if saved.response_mode == "popup":
        return _popup_response(request, payload={**payload, "message": detail}, success=False)
    raise HTTPException(status_code=status_code, detail=detail)


@router.get("/oauth/{provider}/callback", name="crm_oauth_callback", response_model=None)
async def crm_oauth_callback(
    provider: str,
    request: Request,
    session: DB,
    state: str = Query(min_length=20, max_length=512),
    code: str | None = Query(default=None, min_length=1, max_length=4096),
    error: str | None = Query(default=None, max_length=512),
    error_description: str | None = Query(default=None, max_length=1000),
) -> dict[str, Any] | HTMLResponse:
    try:
        saved = await oauth_state_store.consume(state)
    except OAuthStateError as exc:
        raise HTTPException(
            status_code=400, detail="OAuth state is invalid, expired, or already used"
        ) from exc
    if saved.provider != provider:
        raise HTTPException(status_code=400, detail="OAuth provider does not match the authorization state")

    await set_tenant_context(session, saved.tenant_id)
    try:
        connection, workspace_id = await _callback_connection(session, saved=saved, provider=provider)
    except HTTPException as exc:
        return _callback_failure(
            request,
            saved,
            detail=str(exc.detail),
            payload={"connectionId": str(saved.connection_id), "provider": provider},
            status_code=exc.status_code,
        )
    if error or not code:
        connection.status = CRMConnectionStatus.AUTH_REQUIRED.value
        connection.last_failure_at = datetime.now(UTC)
        connection.last_error = f"OAuth authorization failed: {error or 'missing_code'}"[:1000]
        record_audit_event(
            session,
            tenant_id=saved.tenant_id,
            workspace_id=workspace_id,
            actor_user_id=saved.user_id,
            action="crm.oauth.denied",
            entity_type="crm_connection",
            entity_id=str(connection.id),
            category="crm",
            severity="warning",
            outcome="failure",
            after={"provider": provider, "status": connection.status},
            metadata={"providerError": error or "missing_code"},
        )
        await session.commit()
        return _callback_failure(
            request,
            saved,
            detail=error_description or "CRM authorization was not completed",
            payload={
                "connectionId": str(connection.id),
                "provider": provider,
                "status": connection.status,
            },
            status_code=400,
        )

    try:
        provider_enum = CRMProvider(provider)
        connector = crm_registry.get(provider_enum)
        existing = _decrypt_credentials(connection)
        context = CRMConnectionContext(
            tenant_id=saved.tenant_id,
            connection_id=connection.id,
            provider=provider_enum,
            configuration=connection.configuration_json,
            credentials=existing,
        )
        updated = await connector.exchange_authorization_code(
            context,
            code=code,
            redirect_uri=saved.redirect_uri,
            code_verifier=(
                saved.code_verifier if bool(connection.configuration_json.get("pkce", False)) else None
            ),
        )
        connection.credentials_encrypted = credential_store.encrypt(updated)
        connection.last_authenticated_at = datetime.now(UTC)
        connected_context = CRMConnectionContext(
            tenant_id=saved.tenant_id,
            connection_id=connection.id,
            provider=provider_enum,
            configuration=connection.configuration_json,
            credentials=updated,
        )
        health = await connector.health_check(connected_context)
        connection.status = health.status.value
        connection.last_health_at = datetime.now(UTC)
        connection.last_error = (
            None
            if health.status.value == CRMConnectionStatus.HEALTHY.value
            else str(health.details.get("error") or "Health validation failed")[:1000]
        )
        if health.status.value != CRMConnectionStatus.HEALTHY.value:
            connection.last_failure_at = datetime.now(UTC)
            await session.commit()
            return _callback_failure(
                request,
                saved,
                detail="CRM authorization succeeded, but the provider health check failed",
                payload={
                    "connectionId": str(connection.id),
                    "provider": connection.provider,
                    "status": connection.status,
                },
                status_code=409,
            )

        provisioning = await provision_connection(
            session,
            tenant_id=saved.tenant_id,
            workspace_id=workspace_id,
            connection=connection,
            credentials=updated,
        )
        connection.last_success_at = datetime.now(UTC)
        record_audit_event(
            session,
            tenant_id=saved.tenant_id,
            workspace_id=workspace_id,
            actor_user_id=saved.user_id,
            action="crm.one_click.connected",
            entity_type="crm_connection",
            entity_id=str(connection.id),
            category="crm",
            after={
                "provider": connection.provider,
                "status": connection.status,
                "ready": provisioning.readiness.ready,
                "mappingVersion": provisioning.readiness.mapping_version,
                "schemaFieldCount": provisioning.schema_field_count,
                "autoSyncNewLeads": provisioning.readiness.auto_sync_new_leads,
                "autoSyncUpdates": provisioning.readiness.auto_sync_updates,
            },
        )
        await session.commit()
        readiness = provisioning.readiness
    except (CRMError, CredentialStoreError, ValueError) as exc:
        connection.status = CRMConnectionStatus.CONFIGURATION_ERROR.value
        connection.last_failure_at = datetime.now(UTC)
        connection.last_error = "OAuth completed, but automatic CRM provisioning failed"
        record_audit_event(
            session,
            tenant_id=saved.tenant_id,
            workspace_id=workspace_id,
            actor_user_id=saved.user_id,
            action="crm.one_click.provisioning_failed",
            entity_type="crm_connection",
            entity_id=str(connection.id),
            category="crm",
            severity="warning",
            outcome="failure",
            after={"provider": connection.provider, "status": connection.status},
            metadata={"errorType": type(exc).__name__},
        )
        await session.commit()
        return _callback_failure(
            request,
            saved,
            detail="CRM authorization completed, but automatic setup could not be finished",
            payload={
                "connectionId": str(connection.id),
                "provider": connection.provider,
                "status": connection.status,
            },
            status_code=409,
        )

    result = {
        "connected": connection.status == CRMConnectionStatus.HEALTHY.value,
        "connectionId": str(connection.id),
        "provider": connection.provider,
        "status": connection.status,
        "workspaceId": str(workspace_id),
        "readiness": readiness.as_dict(),
    }
    if saved.response_mode == "popup":
        return _popup_response(
            request,
            payload={**result, "message": "CRM connected and automatic Lead sync is ready."},
            success=readiness.ready,
        )
    return result
