"""Preserve task signatures across Celery's untyped registration boundary."""

from collections.abc import Callable
from typing import Protocol, cast

from northstar_api.workers.celery_app import celery_app


class RegisteredTask[**P, R](Protocol):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...

    def apply_async(self, *args: object, **kwargs: object) -> object: ...


def register_task[**P, R](**options: object) -> Callable[[Callable[P, R]], RegisteredTask[P, R]]:
    decorator = celery_app.task(**options)

    def register(function: Callable[P, R]) -> RegisteredTask[P, R]:
        task = decorator(function)
        if not callable(task) or not callable(getattr(task, "apply_async", None)):
            raise TypeError("Celery registration did not return a callable dispatchable task")
        # The function signature is retained by Celery; only its framework
        # wrapper lacks published type information. Validate that boundary here.
        return cast(RegisteredTask[P, R], task)

    return register
