"""Synchronize global help content during a privileged migration release job."""

from __future__ import annotations

import asyncio
from urllib.parse import urlsplit

from sqlalchemy.ext.asyncio import async_sessionmaker

from northstar_api.config import get_settings
from northstar_api.database import build_engine
from northstar_api.services.help_content import sync_help_content


async def main() -> None:
    settings = get_settings()
    if settings.is_production and urlsplit(settings.database_url).username == "talktobot_runtime":
        raise RuntimeError("Help content synchronization requires the separate migration credential")
    engine = build_engine(settings, apply_runtime_role=False)
    try:
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            await sync_help_content(session)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
