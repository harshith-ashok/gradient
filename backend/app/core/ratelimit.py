"""Failed-login throttling on Redis. It fails open: if Redis is down, sign-in still works."""

import logging

from app.core import cache
from app.core.config import get_settings

log = logging.getLogger(__name__)


def _key(scope: str, ident: str) -> str:
    return f"rl:login:{scope}:{ident.lower()}"


def blocked(email: str, ip: str) -> int:
    """Seconds the caller must wait, or 0 if sign-in may proceed."""
    s = get_settings()
    try:
        c = cache._client()
        for key, limit in ((_key("acct", f"{email}|{ip}"), s.login_max_failures),
                           (_key("ip", ip), s.login_max_failures_per_ip)):
            n = c.get(key)
            if n is not None and int(n) >= limit:
                return max(int(c.ttl(key)), 1)
    except Exception:  # noqa: BLE001
        log.warning("rate limit check failed", exc_info=True)
    return 0


def record_failure(email: str, ip: str) -> None:
    window = get_settings().login_window_minutes * 60
    try:
        c = cache._client()
        for key in (_key("acct", f"{email}|{ip}"), _key("ip", ip)):
            if c.incr(key) == 1:
                c.expire(key, window)
    except Exception:  # noqa: BLE001
        log.warning("rate limit record failed", exc_info=True)


def clear(email: str, ip: str) -> None:
    cache.invalidate(_key("acct", f"{email}|{ip}"))
