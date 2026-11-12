from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IdMixin, utcnow

LOG_LEVELS = ("INFO", "WARNING", "ERROR", "CRITICAL")
ISSUE_STATUSES = ("open", "resolved", "ignored")


class LogEntry(IdMixin, Base):
    """One API request (method/path/status/duration set) or one warning-or-worse log record.

    Kept in the database so the admin dashboard can search it; old rows are pruned
    (`LOG_RETENTION_DAYS`). Request bodies, cookies and headers are never stored.
    """

    __tablename__ = "log_entries"
    __table_args__ = (CheckConstraint(f"level IN {LOG_LEVELS}", name="ck_log_entries_level"),)

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    level: Mapped[str] = mapped_column(String(10), index=True)
    source: Mapped[str] = mapped_column(String(10), default="api")  # api | worker
    logger: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    method: Mapped[str | None] = mapped_column(String(8))
    path: Mapped[str | None] = mapped_column(String(255))  # the route template, e.g. /courses/{course_id}
    status: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    user_id: Mapped[str | None] = mapped_column(String(40))
    role: Mapped[str | None] = mapped_column(String(16))


class Issue(IdMixin, Base):
    """Unhandled errors grouped by where they happen, so one bug is one row however often it fires."""

    __tablename__ = "issues"
    __table_args__ = (CheckConstraint(f"status IN {ISSUE_STATUSES}", name="ck_issues_status"),)

    fingerprint: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(300))  # "ValueError: bad thing"
    exc_type: Mapped[str] = mapped_column(String(120))
    culprit: Mapped[str] = mapped_column(String(255))  # file:function where it was raised
    source: Mapped[str] = mapped_column(String(10), default="api")
    status: Mapped[str] = mapped_column(String(10), default="open", index=True)
    count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    note: Mapped[str | None] = mapped_column(String(500))


class IssueEvent(IdMixin, Base):
    __tablename__ = "issue_events"

    issue_id: Mapped[str] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    message: Mapped[str] = mapped_column(Text)
    stack_trace: Mapped[str] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(64))
    method: Mapped[str | None] = mapped_column(String(8))
    path: Mapped[str | None] = mapped_column(String(255))
    user_id: Mapped[str | None] = mapped_column(String(40))
