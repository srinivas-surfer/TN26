"""
Lightweight TTL cache — avoids repeated DB/ML calls on t2.micro.
Uses cachetools.TTLCache wrapped in a simple async-safe helper.
"""
import asyncio
import functools
import time
import logging
from typing import Any, Callable, Optional
from cachetools import TTLCache

logger = logging.getLogger("tn2026.cache")

# Global caches with different TTLs
_caches = {
    "short": TTLCache(maxsize=50, ttl=60),      # 1 min — live results
    "medium": TTLCache(maxsize=100, ttl=300),   # 5 min — trends/predictions
    "long": TTLCache(maxsize=50, ttl=3600),     # 1 hr — historical
}


def cache_get(key: str, tier: str = "medium") -> Optional[Any]:
    return _caches[tier].get(key)


def cache_set(key: str, value: Any, tier: str = "medium") -> None:
    _caches[tier][key] = value


def cache_invalidate(tier: str = "medium") -> None:
    _caches[tier].clear()
    logger.info(f"Cache tier '{tier}' cleared")


def cached(tier: str = "medium", key_fn: Optional[Callable] = None):
    """Decorator for async functions."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if key_fn:
                cache_key = key_fn(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"

            hit = cache_get(cache_key, tier)
            if hit is not None:
                return hit

            result = await func(*args, **kwargs)
            if result is not None:
                cache_set(cache_key, result, tier)
            return result
        return wrapper
    return decorator


def get_cache_stats() -> dict:
    return {
        tier: {"size": len(c), "maxsize": c.maxsize, "ttl": c.ttl}
        for tier, c in _caches.items()
    }
