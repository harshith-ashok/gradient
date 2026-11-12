"""Single time source. Services call now()/today() so tests and the demo seed can move time."""

from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings

_offset = timedelta(0)


def now() -> datetime:
    return datetime.now(UTC) + _offset


def today() -> date:
    """Calendar date in the configured timezone: this decides which plan day it is."""
    return now().astimezone(ZoneInfo(get_settings().app_timezone)).date()


def set_days_ago(n: int) -> None:
    global _offset
    _offset = -timedelta(days=n)


def reset() -> None:
    global _offset
    _offset = timedelta(0)


@contextmanager
def days_ago(n: int):
    set_days_ago(n)
    try:
        yield
    finally:
        reset()
