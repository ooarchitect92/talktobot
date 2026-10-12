from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from northstar_api import main


@pytest.mark.parametrize("production", [True, False])
async def test_production_startup_does_not_write_global_help_content(monkeypatch, production: bool):
    monkeypatch.setattr(
        main,
        "settings",
        SimpleNamespace(
            app_auto_create_schema=False,
            is_production=production,
            app_env="production" if production else "test",
        ),
    )
    monkeypatch.setattr(main, "help_settings", SimpleNamespace(help_content_sync_on_startup=True))
    monkeypatch.setattr(main, "SessionFactory", MagicMock(return_value=AsyncMock()))
    monkeypatch.setattr(main, "seed_from_environment", AsyncMock())
    synchronization = AsyncMock()
    monkeypatch.setattr(main, "sync_help_content", synchronization)
    monkeypatch.setattr(main, "close_database", AsyncMock())
    monkeypatch.setattr(main.redis_services, "close", AsyncMock())
    async with main.lifespan(main.app):
        pass
    assert synchronization.await_count == (0 if production else 1)
