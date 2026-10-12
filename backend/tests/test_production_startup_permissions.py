from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from northstar_api import main


@pytest.mark.parametrize(
    "production,postgres,auto_schema,runtime_role,expected",
    [
        (True, True, False, True, 0),
        (False, False, False, True, 1),
        (False, True, False, True, 0),
        (False, True, False, False, 1),
        (False, False, True, True, 1),
    ],
)
async def test_restricted_startup_does_not_write_global_help_content(
    monkeypatch, production: bool, postgres: bool, auto_schema: bool, runtime_role: bool, expected: int
):
    monkeypatch.setattr(
        main,
        "settings",
        SimpleNamespace(
            app_auto_create_schema=auto_schema,
            is_postgres=postgres,
            database_apply_runtime_role=runtime_role,
            is_production=production,
            app_env="production" if production else "test",
        ),
    )
    monkeypatch.setattr(main, "help_settings", SimpleNamespace(help_content_sync_on_startup=True))
    monkeypatch.setattr(main, "SessionFactory", MagicMock(return_value=AsyncMock()))
    monkeypatch.setattr(main, "seed_from_environment", AsyncMock())
    monkeypatch.setattr(main, "initialize_schema", AsyncMock())
    synchronization = AsyncMock()
    monkeypatch.setattr(main, "sync_help_content", synchronization)
    monkeypatch.setattr(main, "close_database", AsyncMock())
    monkeypatch.setattr(main.redis_services, "close", AsyncMock())
    async with main.lifespan(main.app):
        pass
    assert synchronization.await_count == expected
