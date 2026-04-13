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
        try:
            result = fn()
            self.failure_count = 0
            return result
        except Exception as first_error:  # noqa: BLE001
            self.failure_count += 1
            if self.failure_count > self.max_failures:
                raise CircuitOpenError(
                    f"Circuit open after {self.failure_count} failures"
                ) from first_error

            self.sleep_fn(self.backoff_seconds)

            try:
                result = fn()
                self.failure_count = 0
                return result
            except Exception as second_error:  # noqa: BLE001
                self.failure_count += 1
                if self.failure_count > self.max_failures:
                    raise CircuitOpenError(
                        f"Circuit open after {self.failure_count} failures"
                    ) from second_error
                raise


__all__ = ["CircuitBreaker", "CircuitOpenError"]
