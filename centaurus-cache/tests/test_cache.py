"""Cache tests — hit/miss, TTL, normalization, eviction."""
import time


from centaurus_cache import ResponseCache, cache_key


class TestKeyNormalization:
    def test_whitespace_collapsed(self):
        assert cache_key('SEO  について') == cache_key('SEO について')

    def test_case_insensitive(self):
        assert cache_key('SEO') == cache_key('seo')

    def test_full_half_width_unified(self):
        assert cache_key('ＳＥＯ') == cache_key('SEO')

    def test_extra_distinguishes(self):
        assert cache_key('q', extra='intent_a') != cache_key('q', extra='intent_b')


class TestCacheGetSet:
    def test_miss_returns_none(self):
        c = ResponseCache(ttl_seconds=10)
        assert c.get('k') is None

    def test_set_then_get_hit(self):
        c = ResponseCache(ttl_seconds=10)
        c.set('k', {'text': 'hi'})
        assert c.get('k') == {'text': 'hi'}

    def test_ttl_expiry(self):
        c = ResponseCache(ttl_seconds=0.05)
        c.set('k', {'text': 'hi'})
        time.sleep(0.1)
        assert c.get('k') is None

    def test_stats(self):
        c = ResponseCache(ttl_seconds=10)
        c.set('k', {'x': 1})
        c.get('k')  # hit
        c.get('m')  # miss
        s = c.stats()
        assert s['hits'] == 1
        assert s['misses'] == 1
        assert 0 < s['hit_rate'] < 1

    def test_invalidate_all(self):
        c = ResponseCache(ttl_seconds=10)
        c.set('a', {'1': 1}); c.set('b', {'2': 2})
        c.invalidate()
        assert c.get('a') is None and c.get('b') is None

    def test_invalidate_one(self):
        c = ResponseCache(ttl_seconds=10)
        c.set('a', {'1': 1}); c.set('b', {'2': 2})
        c.invalidate('a')
        assert c.get('a') is None
        assert c.get('b') == {'2': 2}

    def test_eviction_under_max(self):
        c = ResponseCache(ttl_seconds=10, max_entries=10)
        for i in range(15):
            c.set(f'k{i}', {'v': i})
        # at least some old entries should be evicted
        assert c.stats()['size'] <= 10
