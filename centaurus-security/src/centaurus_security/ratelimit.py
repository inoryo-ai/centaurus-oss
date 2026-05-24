"""In-memory token-bucket rate limiter.

Per-key (typically user_id) limit. Thread-safe via lock.
For multi-instance deploys, swap with Redis-backed impl behind same API.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass


class RateLimitExceeded(Exception):
    def __init__(self, key: str, retry_after_sec: float):
        super().__init__(f'rate limit exceeded for {key}, retry in {retry_after_sec:.1f}s')
        self.key = key
        self.retry_after_sec = retry_after_sec


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    """Token bucket per key.

    Defaults: 10 requests / 60 seconds per key (matches A7 spec).
    """

    def __init__(self, *, capacity: int = 10, refill_seconds: float = 60.0):
        self.capacity = float(capacity)
        self.refill_rate = self.capacity / refill_seconds  # tokens per sec
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def check(self, key: str, *, cost: float = 1.0) -> None:
        """Raise RateLimitExceeded if no token. Else consume `cost`."""
        now = time.monotonic()
        with self._lock:
            b = self._buckets.get(key)
            if b is None:
                b = _Bucket(tokens=self.capacity - cost, last_refill=now)
                self._buckets[key] = b
                if b.tokens < 0:
                    b.tokens = 0
                    raise RateLimitExceeded(key, cost / self.refill_rate)
                return

            elapsed = now - b.last_refill
            b.tokens = min(self.capacity, b.tokens + elapsed * self.refill_rate)
            b.last_refill = now

            if b.tokens >= cost:
                b.tokens -= cost
                return

            deficit = cost - b.tokens
            retry = deficit / self.refill_rate
            raise RateLimitExceeded(key, retry)

    def snapshot(self, key: str) -> dict | None:
        with self._lock:
            b = self._buckets.get(key)
            if b is None:
                return None
            return {'tokens': round(b.tokens, 2),
                    'capacity': self.capacity,
                    'last_refill_age_sec': round(time.monotonic() - b.last_refill, 2)}
