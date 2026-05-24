"""Adapter base — ABC, registry, structured logging, env-flag gating."""
from __future__ import annotations

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

logger = logging.getLogger('centaurus.adapters')
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('[%(name)s] %(message)s'))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)


@dataclass
class AdapterCallResult:
    ok: bool
    adapter: str
    op: str
    latency_ms: float
    payload_size: int = 0
    data: Any = None
    error: str | None = None
    dry_run: bool = False
    meta: dict = field(default_factory=dict)

    def to_log_dict(self) -> dict:
        return {
            'ok': self.ok,
            'adapter': self.adapter,
            'op': self.op,
            'latency_ms': round(self.latency_ms, 2),
            'payload_size': self.payload_size,
            'dry_run': self.dry_run,
            'error': self.error,
            'meta': self.meta,
        }


class AdapterBase(ABC):
    """Abstract base for all adapters.

    Subclasses MUST set:
      - NAME: short identifier (e.g. 'feedback', 'quiz')
      - ENV_FLAG: env var name; if value in ENABLED_VALUES → enabled
    """

    NAME: ClassVar[str] = 'base'
    ENV_FLAG: ClassVar[str] = 'CTR_BASE_ENABLED'
    ENABLED_VALUES: ClassVar[set[str]] = {'1', 'true', 'TRUE', 'yes', 'on'}

    def __init__(self, dry_run: bool = False, force_enabled: bool | None = None):
        self._dry_run = dry_run
        self._force_enabled = force_enabled

    @property
    def enabled(self) -> bool:
        if self._force_enabled is not None:
            return self._force_enabled
        v = os.environ.get(self.ENV_FLAG, '').strip()
        return v in self.ENABLED_VALUES

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    def health(self) -> dict:
        """Return adapter health snapshot."""
        return {
            'name': self.NAME,
            'enabled': self.enabled,
            'dry_run': self.dry_run,
            'env_flag': self.ENV_FLAG,
        }

    def _emit(self, result: AdapterCallResult) -> None:
        try:
            logger.info(json.dumps(result.to_log_dict(), ensure_ascii=False))
        except Exception:
            logger.info(f'[{result.adapter}] {result.op} ok={result.ok}')

    def _call(self, op: str, fn, payload: Any = None) -> AdapterCallResult:
        """Wrap a concrete operation with timing + structured logging.

        - If adapter disabled → returns ok=True with data=None (no-op).
        - If dry_run → returns ok=True without calling fn.
        - On exception → ok=False, error captured, never raised.
        """
        if not self.enabled:
            r = AdapterCallResult(
                ok=True, adapter=self.NAME, op=op, latency_ms=0.0,
                data=None, meta={'reason': 'disabled'})
            self._emit(r)
            return r

        if self.dry_run:
            size = self._size(payload)
            r = AdapterCallResult(
                ok=True, adapter=self.NAME, op=op, latency_ms=0.0,
                payload_size=size, dry_run=True, data=None,
                meta={'reason': 'dry_run', 'payload_preview': self._preview(payload)})
            self._emit(r)
            return r

        t0 = time.perf_counter()
        try:
            data = fn()
            ms = (time.perf_counter() - t0) * 1000
            r = AdapterCallResult(
                ok=True, adapter=self.NAME, op=op, latency_ms=ms,
                payload_size=self._size(payload), data=data)
            self._emit(r)
            return r
        except Exception as e:
            ms = (time.perf_counter() - t0) * 1000
            r = AdapterCallResult(
                ok=False, adapter=self.NAME, op=op, latency_ms=ms,
                payload_size=self._size(payload), error=f'{type(e).__name__}: {e}')
            self._emit(r)
            return r

    @staticmethod
    def _size(payload: Any) -> int:
        if payload is None:
            return 0
        try:
            return len(json.dumps(payload, ensure_ascii=False))
        except Exception:
            return len(str(payload))

    @staticmethod
    def _preview(payload: Any, limit: int = 120) -> str:
        if payload is None:
            return ''
        try:
            s = json.dumps(payload, ensure_ascii=False)
        except Exception:
            s = str(payload)
        return s[:limit] + ('…' if len(s) > limit else '')

    @abstractmethod
    def _ops(self) -> list[str]:
        """List supported operations for introspection."""


class AdapterRegistry:
    """Global registry of adapter instances. Resolve by name at runtime."""

    def __init__(self) -> None:
        self._by_name: dict[str, AdapterBase] = {}

    def register(self, adapter: AdapterBase) -> None:
        self._by_name[adapter.NAME] = adapter

    def get(self, name: str) -> AdapterBase | None:
        return self._by_name.get(name)

    def health_all(self) -> list[dict]:
        return [a.health() | {'ops': a._ops()} for a in self._by_name.values()]

    def names(self) -> list[str]:
        return list(self._by_name)


registry = AdapterRegistry()
