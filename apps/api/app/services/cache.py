import hashlib
import time
from typing import Any, Optional


class SimpleTTLCache:
    """
    Lightweight in-memory TTL cache (dev-friendly).
    """

    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self.store = {}

    def _now(self):
        return time.time()

    def _make_key(self, key: str) -> str:
        return hashlib.md5(key.encode()).hexdigest()

    def set(self, key: str, value: Any):
        k = self._make_key(key)
        self.store[k] = {
            "value": value,
            "time": self._now()
        }

    def get(self, key: str) -> Optional[Any]:
        k = self._make_key(key)

        if k not in self.store:
            return None

        entry = self.store[k]

        if self._now() - entry["time"] > self.ttl:
            del self.store[k]
            return None

        return entry["value"]

    def clear(self):
        self.store = {}


# =========================
# 🔥 SINGLETON CACHE (IMPORTANT FIX)
# =========================

_cache_instance = SimpleTTLCache(ttl_seconds=300)


def get_cache() -> SimpleTTLCache:
    """
    Global cache instance used by RAG service.
    """
    return _cache_instance