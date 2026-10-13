"""Deliver recovery material privately without exposing it through the API."""

from __future__ import annotations

import asyncio
from email.message import EmailMessage

from northstar_api.config import get_settings
from northstar_api.email_config import get_email_settings
from northstar_api.models import User
from northstar_api.services.smtp import smtp_send


async def send_mfa_recovery_codes(user: User, codes: list[str]) -> None:
    settings = get_email_settings()
    if settings.email_delivery_mode != "smtp":
        if get_settings().app_env == "test":
            return
        raise RuntimeError("Recovery email delivery is not configured")
    message = EmailMessage()
    message["Subject"] = "TalkToBot authenticator recovery codes"
    message["From"] = f"{settings.email_from_name} <{settings.email_from_address}>"
    message["To"] = user.email
    message.set_content(
        "Keep these recovery codes private. Each code can be used once if you lose "
        "access to your authenticator. This set replaces earlier recovery codes.\n\n"
        + "\n".join(codes)
        + "\n\nComplete authenticator setup using the QR code and its six-digit code. "
        "TalkToBot support will never ask you to send these codes.\n"
    )
    await asyncio.to_thread(smtp_send, message, settings)
