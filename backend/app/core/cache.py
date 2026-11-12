"""Small JSON cache on Redis. It fails open: if Redis is down, callers just hit the database."""

import json
import logging
from collections.abc import Callable
from typing import Any, Protocol

import redis

from app.core.config import get_settings

log = logging.getLogger(__name__)


class CacheBackend(Protocol):
    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: str, ex: int | None = None) -> Any: ...
    def delete(self, *keys: str) -> Any: ...


_backend: CacheBackend | None = None


def set_backend(backend: CacheBackend | None) -> None:
    """Swap the backend (tests use an in-memory fake)."""
    global _backend
    _backend = backend


def _client() -> CacheBackend:
    global _backend
    if _backend is None:
        _backend = redis.Redis.from_url(
            get_settings().redis_url, socket_connect_timeout=0.5, socket_timeout=0.5
        )
    return _backend


def cached_json(key: str, ttl: int, loader: Callable[[], Any]) -> Any:
    try:
        hit = _client().get(key)
        if hit is not None:
            return json.loads(hit)
    except Exception:
        log.warning("cache read failed for %s", key, exc_info=True)
    value = loader()
    try:
        _client().set(key, json.dumps(value), ex=ttl)
    except Exception:
        log.warning("cache write failed for %s", key, exc_info=True)
    return value


def invalidate(*keys: str) -> None:
    try:
        _client().delete(*keys)
    except Exception:
        log.warning("cache invalidate failed for %s", keys, exc_info=True)


def course_key(course_id: str) -> str:
    return f"course:structure:{course_id}"
