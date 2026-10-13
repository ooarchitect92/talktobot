"""Resolve provider activation only after tenant and workspace authentication."""

from fastapi import HTTPException, Request
from sqlalchemy import select

from northstar_api.dependencies import DBSession, get_current_principal
from northstar_api.services.entitlement_guard import Credentials
from northstar_api.services.release_capabilities import (
    capability_enabled,
    provider_enabled,
    scoped_provider_request,
)


async def enforce_integration_release(request: Request, credentials: Credentials, session: DBSession) -> None:
    category = scoped_provider_request(request.url.path, request.method)
    if not category or capability_enabled(category):
        return
    principal = await get_current_principal(request, credentials, session)
    connection_id: object = request.path_params.get("connection_id")
    from uuid import UUID

    from northstar_api.lead_crm.channel_models import ChannelConnection, ChannelOutboundDelivery
    from northstar_api.lead_crm.channel_scope import WorkspaceChannelConnection
    from northstar_api.lead_crm.models import CRMConnection, CRMDelivery, RawWebhookEvent
    from northstar_api.lead_crm.workspace_scope import WorkspaceCRMConnection
    from northstar_api.models import Lead

    model: type[ChannelConnection] | type[CRMConnection]
    scope: type[WorkspaceChannelConnection] | type[WorkspaceCRMConnection]
    if category == "channels":
        model, scope = ChannelConnection, WorkspaceChannelConnection
        if connection_id is None:
            try:
                event_id = UUID(
                    str(request.path_params.get("event_id") or request.path_params.get("delivery_id"))
                )
            except ValueError:
                raise HTTPException(422, "Invalid event identifier") from None
            if "event_id" in request.path_params:
                connection_id = await session.scalar(
                    select(RawWebhookEvent.connection_key).where(
                        RawWebhookEvent.id == event_id,
                        RawWebhookEvent.tenant_id == principal.tenant_id,
                    )
                )
            else:
                connection_id = await session.scalar(
                    select(ChannelOutboundDelivery.connection_id).where(
                        ChannelOutboundDelivery.id == event_id,
                        ChannelOutboundDelivery.tenant_id == principal.tenant_id,
                    )
                )
    else:
        model, scope = CRMConnection, WorkspaceCRMConnection
        if connection_id is None:
            try:
                delivery_id = UUID(str(request.path_params.get("delivery_id", "")))
            except ValueError:
                raise HTTPException(422, "Invalid delivery identifier") from None
            connection_id = await session.scalar(
                select(CRMDelivery.connection_id)
                .join(Lead, Lead.id == CRMDelivery.lead_id)
                .where(
                    CRMDelivery.id == delivery_id,
                    CRMDelivery.tenant_id == principal.tenant_id,
                    Lead.tenant_id == principal.tenant_id,
                    Lead.workspace_id == principal.workspace_id,
                )
            )
    if connection_id is None:
        raise HTTPException(404, "Connection not found in this workspace")
    try:
        identifier = UUID(str(connection_id))
    except ValueError:
        raise HTTPException(422, "Invalid connection identifier") from None
    provider = await session.scalar(
        select(model.provider)
        .join(scope, scope.connection_id == model.id)
        .where(
            model.id == identifier,
            model.tenant_id == principal.tenant_id,
            scope.tenant_id == principal.tenant_id,
            scope.workspace_id == principal.workspace_id,
        )
    )
    if provider is None:
        raise HTTPException(404, "Connection not found in this workspace")
    if not provider_enabled(provider):
        raise HTTPException(503, "This provider is not enabled in this release")
