from typing import Any

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from northstar_api.config import get_settings
from northstar_api.lead_crm.credentials import credential_store
from northstar_api.models import WhatsAppBusinessAccount, WhatsAppConnection
from northstar_api.services.whatsapp import (
    WhatsAppCloudClient,
    WhatsAppConfigurationError,
    token_cipher,
    whatsapp_client,
)


def _required_credential(values: dict[str, Any], field: str) -> str:
    value = values.get(field)
    if not isinstance(value, str) or not value.strip():
        raise WhatsAppConfigurationError("WhatsApp account credentials are incomplete")
    return value


def account_client(account: WhatsAppBusinessAccount) -> tuple[WhatsAppCloudClient, str]:
    credentials = credential_store.decrypt(account.credentials_encrypted)
    settings = get_settings().model_copy(
        update={
            "meta_app_id": account.app_id,
            "meta_app_secret": SecretStr(_required_credential(credentials, "app_secret")),
            "meta_whatsapp_webhook_verify_token": SecretStr(
                _required_credential(credentials, "verify_token")
            ),
        }
    )
    return WhatsAppCloudClient(settings), _required_credential(credentials, "access_token")


async def connection_client(
    session: AsyncSession, connection: WhatsAppConnection
) -> tuple[WhatsAppCloudClient, str]:
    if connection.business_account_id:
        account = await session.get(WhatsAppBusinessAccount, connection.business_account_id)
        if (
            not account
            or account.workspace_id != connection.workspace_id
            or account.tenant_id != connection.tenant_id
        ):
            raise WhatsAppConfigurationError("WhatsApp account is unavailable")
        return account_client(account)
    return whatsapp_client, token_cipher.decrypt(connection.access_token_encrypted)
