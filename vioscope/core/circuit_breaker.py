from __future__ import annotations

import time
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised when the circuit is open after exceeding allowed failures."""


class CircuitBreaker(Generic[T]):
    def __init__(
        self,
        max_failures: int = 1,
        backoff_seconds: float = 0.5,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self.max_failures = max_failures
        self.backoff_seconds = backoff_seconds
        self.sleep_fn = sleep_fn or time.sleep
        self.failure_count = 0

    def call(self, fn: Callable[[], T]) -> T:
        last_exc: BaseException | None = None
        for attempt in range(self.max_failures + 1):
            try:
                result = fn()
                self.failure_count = 0
                return result
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self.failure_count += 1
                if self.max_failures == 0:
                    raise CircuitOpenError("Circuit open: threshold is zero") from exc
                if self.failure_count > self.max_failures:
                    raise CircuitOpenError(
                        f"Circuit open after {self.failure_count} failures"
                    ) from exc
                if self.failure_count == self.max_failures and self.max_failures > 1:
                    raise exc
                if attempt < self.max_failures:
                    self.sleep_fn(self.backoff_seconds)
        # Unreachable: loop always raises CircuitOpenError before exhausting attempts
        raise CircuitOpenError(  # pragma: no cover
            f"Circuit open after {self.failure_count} failures"
        ) from last_exc


__all__ = ["CircuitBreaker", "CircuitOpenError"]
