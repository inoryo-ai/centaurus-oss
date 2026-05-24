"""Response cache for chat replies.

Key: SHA1(normalized_query + intent_hint).
Value: serialized AssistantResponse fields.
TTL: configurable (default 30min).

Why: 大半の質問は重複する（料金・退会・SEO・GA4 等）。
キャッシュヒット時はLLM呼び出しを完全スキップしてP95を大幅に削減。

Thread-safe via lock. Single-instance only — for multi-instance deploy
swap with Redis-backed adapter behind same API.
"""
from __future__ import annotations

import hashlib
import threading
import time
import unicodedata
from dataclasses import dataclass


def _normalize(query: str) -> str:
    """Make functionally-equivalent queries hash to same key."""
    s = unicodedata.normalize('NFKC', query.strip().lower())
    # collapse whitespace
    return ' '.join(s.split())


def cache_key(query: str, *, extra: str = '') -> str:
    norm = _normalize(query)
    return hashlib.sha1((norm + '|' + extra).encode('utf-8')).hexdigest()


@dataclass
class CacheEntry:
    payload: dict
    expires_at: float
    hit_count: int = 0


class ResponseCache:
    def __init__(self, *, ttl_seconds: float = 1800.0, max_entries: int = 1000):
        self.ttl = float(ttl_seconds)
        self.max = int(max_entries)
        self._store: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> dict | None:
        with self._lock:
            e = self._store.get(key)
            if e is None:
                self._misses += 1
                return None
            if e.expires_at < time.time():
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            e.hit_count += 1
            return e.payload

    def set(self, key: str, payload: dict) -> None:
        with self._lock:
            if len(self._store) >= self.max:
                # Evict 10% oldest by expiry
                victims = sorted(self._store.items(),
                                 key=lambda kv: kv[1].expires_at)[:max(1, self.max // 10)]
                for k, _ in victims:
                    del self._store[k]
            self._store[key] = CacheEntry(
                payload=payload, expires_at=time.time() + self.ttl)

    def invalidate(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._store.clear()
            else:
                self._store.pop(key, None)

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total else 0.0
            return {
                'size': len(self._store),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 4),
                'ttl_seconds': self.ttl,
                'max_entries': self.max,
            }
