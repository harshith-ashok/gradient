"""Capture request logs, warnings and unhandled exceptions for the admin dashboard.

Nothing here may ever break a request: every write is wrapped, and failures go to stderr only.
Request bodies, headers and cookies are never stored, and secrets that can show up inside
exception text (password hashes, tokens) are masked before saving.
"""

import hashlib
import logging
import random
import re
import sys
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import session_factory
from app.models import Issue, IssueEvent, LogEntry
from app.models.base import utcnow

MAX_MESSAGE = 2000
MAX_TRACE = 20000
MAX_EVENTS_PER_ISSUE = 25
PRUNE_ODDS = 0.005  # about one write in 200 also deletes expired rows

_SECRETS = [
    (re.compile(r"\$argon2[^\s'\"]+"), "[hash]"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*"), "[token]"),
    (re.compile(r"(?i)(password|secret|token|authorization)(['\"]?\s*[:=]\s*['\"]?)[^\s,'\"})]+"), r"\1\2[hidden]"),
]


@contextmanager
def open_session() -> Iterator[Session]:
    """Its own session, so logging never shares a transaction with the request. Tests replace this."""
    with session_factory()() as db:
        yield db


def scrub(text: str, limit: int = MAX_MESSAGE) -> str:
    for pattern, repl in _SECRETS:
        text = pattern.sub(repl, text)
    return text if len(text) <= limit else text[:limit] + "…"


def _safe(fn):
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:  # noqa: BLE001 - monitoring must never take the app down
            print(f"monitoring write failed: {type(e).__name__}: {e}", file=sys.stderr)
            return None

    return wrapper


def _maybe_prune(db: Session) -> None:
    if random.random() < PRUNE_ODDS:
        prune(db)


def prune(db: Session) -> int:
    cutoff = utcnow() - timedelta(days=get_settings().log_retention_days)
    n = db.execute(delete(LogEntry).where(LogEntry.ts < cutoff)).rowcount
    db.execute(delete(IssueEvent).where(IssueEvent.ts < cutoff))
    db.commit()
    return n


def level_for(status: int) -> str:
    return "ERROR" if status >= 500 else "WARNING" if status >= 400 else "INFO"


@_safe
def record_request(*, request_id: str, method: str, path: str, status: int, duration_ms: int,
                   user_id: str | None, role: str | None) -> None:
    with open_session() as db:
        db.add(LogEntry(
            level=level_for(status), source=get_settings().log_source, logger="gradient.access",
            message=f"{method} {path} -> {status} in {duration_ms}ms", request_id=request_id,
            method=method, path=path[:255], status=status, duration_ms=duration_ms,
            user_id=user_id, role=role,
        ))
        db.commit()
        _maybe_prune(db)


@_safe
def record_log(*, level: str, logger: str, message: str, request_id: str | None) -> None:
    with open_session() as db:
        db.add(LogEntry(level=level, source=get_settings().log_source, logger=logger[:80],
                        message=scrub(message), request_id=None if request_id in (None, "-") else request_id))
        db.commit()


def fingerprint(exc: BaseException) -> tuple[str, str]:
    """Same bug, same fingerprint: the exception type plus where it was raised (no line numbers,
    so a refactor that moves the line does not split the issue)."""
    frames = traceback.extract_tb(exc.__traceback__)
    own = [f for f in frames
           if "/app/" in f.filename.replace("\\", "/") and not f.filename.endswith("observability.py")]
    f = (own or frames or [None])[-1]
    if f is None:
        culprit = "unknown"
    elif f in own:
        culprit = f"{f.filename.replace(chr(92), '/').split('/app/')[-1]}:{f.name}"
    else:
        culprit = f"{f.filename.replace(chr(92), '/').rsplit('/', 1)[-1]}:{f.name}"
    key = f"{type(exc).__name__}|{culprit}"
    return hashlib.sha1(key.encode()).hexdigest()[:20], culprit


@_safe
def capture_exception(exc: BaseException, *, request_id: str | None = None, method: str | None = None,
                      path: str | None = None, user_id: str | None = None) -> None:
    if getattr(exc, "_gradient_captured", False):  # already counted (e.g. logged after being handled)
        return
    try:
        exc._gradient_captured = True  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - some exception types refuse new attributes
        pass
    fp, culprit = fingerprint(exc)
    message = scrub(str(exc) or type(exc).__name__)
    trace = scrub("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)), MAX_TRACE)
    with open_session() as db:
        issue = db.scalar(select(Issue).where(Issue.fingerprint == fp))
        now = utcnow()
        if issue is None:
            issue = Issue(fingerprint=fp, title=scrub(f"{type(exc).__name__}: {message}", 300),
                          exc_type=type(exc).__name__[:120], culprit=culprit[:255],
                          source=get_settings().log_source, first_seen=now, last_seen=now, count=1)
            db.add(issue)
            db.flush()
        else:
            issue.count += 1
            issue.last_seen = now
            if issue.status == "resolved":  # it came back
                issue.status = "open"
        db.add(IssueEvent(issue_id=issue.id, ts=now, message=message, stack_trace=trace,
                          request_id=request_id, method=method, path=(path or "")[:255] or None,
                          user_id=user_id))
        db.flush()
        old = db.scalars(select(IssueEvent.id).where(IssueEvent.issue_id == issue.id)
                         .order_by(IssueEvent.ts.desc()).offset(MAX_EVENTS_PER_ISSUE)).all()
        if old:
            db.execute(delete(IssueEvent).where(IssueEvent.id.in_(old)))
        db.commit()


class DatabaseLogHandler(logging.Handler):
    """Saves WARNING and above, and turns logged exceptions into issues. Re-entrancy is blocked so a
    failure while saving cannot loop."""

    IGNORED = ("sqlalchemy", "gradient.access", "uvicorn.access", "httpx", "httpcore")
    busy = False

    def __init__(self):
        super().__init__(level=logging.WARNING)

    def emit(self, record: logging.LogRecord) -> None:
        if DatabaseLogHandler.busy or record.name.startswith(self.IGNORED):
            return
        DatabaseLogHandler.busy = True
        try:
            from app.core.observability import request_id

            n = record.levelno
            level = "CRITICAL" if n >= logging.CRITICAL else "ERROR" if n >= logging.ERROR else "WARNING"
            record_log(level=level, logger=record.name, message=record.getMessage(), request_id=request_id.get())
            if record.exc_info and record.exc_info[1] is not None and not record.name.startswith("uvicorn"):
                capture_exception(record.exc_info[1], request_id=request_id.get())
        finally:
            DatabaseLogHandler.busy = False
