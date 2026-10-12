from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest

from northstar_api.config import Settings
from northstar_api.services.rate_limit import RedisServices


@pytest.mark.anyio
async def test_shared_redis_consumption_and_refresh_rotation_are_atomic() -> None:
    url = os.environ.get("REDIS_TEST_URL")
    if not url:
        pytest.skip("Set REDIS_TEST_URL for the real Redis integration check")
    services = RedisServices(Settings(app_env="test", redis_url=url, rate_limit_fail_open=False))
    key = f"integration-{uuid4()}"
    family = f"integration-{uuid4()}"
    try:
        assert await services.ping()
        claims = await asyncio.gather(*(services.claim_once(key) for _ in range(100)))
        assert sum(claims) == 1
        await services.remember_refresh_family(family, "original", 60)
        rotations = await asyncio.gather(
            services.rotate_refresh_family(family, "original", "next-one", 60),
            services.rotate_refresh_family(family, "original", "next-two", 60),
        )
        assert sum(rotations) == 1
        # A replay invalidates the complete family, including the winning successor.
        assert not await services.rotate_refresh_family(family, "next-one", "later", 60)
        assert not await services.rotate_refresh_family(family, "next-two", "later", 60)
    finally:
        await services.client.delete(f"northstar:consumed:{key}", f"northstar:refresh-family:{family}")
        await services.close()
