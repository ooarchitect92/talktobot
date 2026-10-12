from uuid import uuid4

from northstar_api.workers.task_registration import register_task


def test_registered_task_preserves_execution_and_dispatch_interface():
    @register_task(name=f"test.readiness.{uuid4().hex}")
    def increment(value: int, *, step: int = 1) -> int:
        return value + step

    assert increment(4, step=2) == 6
    assert callable(increment.apply_async)
