# centaurus-cache

[![PyPI](https://img.shields.io/pypi/v/centaurus-cache.svg)](https://pypi.org/project/centaurus-cache/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Tiny TTL response cache with normalization-aware keys.
Built for LLM / RAG response caching where queries differ only in whitespace,
case, or full-/half-width characters but should hit the same cache entry.

## Features

- **Normalized cache keys** — NFKC + lowercase + collapsed whitespace.
- **TTL-based expiry**, no background thread (lazy expiry on `get`).
- **LRU-ish eviction** when reaching `max_entries`.
- **Stats** — `size / hits / misses / hit_rate`.
- **Thread-safe.**

## Install

```bash
pip install centaurus-cache
```

## Quick start

```python
from centaurus_cache import ResponseCache, cache_key

cache = ResponseCache(ttl_seconds=1800, max_entries=1000)

key = cache_key('SEOについて教えて', extra='intent=ask_lesson')

if (hit := cache.get(key)) is not None:
    return hit

response = call_llm(query)
cache.set(key, response)

print(cache.stats())
# {'size': 1, 'hits': 0, 'misses': 1, 'hit_rate': 0.0, ...}
```

## Why?

`functools.lru_cache` doesn't support TTL. `cachetools.TTLCache` doesn't
normalize keys. For LLM response caching, both `"SEO について"` and `"ＳＥＯ について"`
should hit the same entry.

## License

MIT
