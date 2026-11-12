from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JSONType
from app.models.base import IdMixin, utcnow

JOB_TYPES = ("analyze", "derive", "generate", "plan")
JOB_STATUSES = ("queued", "running", "succeeded", "failed")


class Job(IdMixin, Base):
    """A unit of background AI work, run by the worker (`python -m app.worker`).

    Kept in Postgres rather than a separate queue: jobs survive restarts, are visible, and can be
    claimed safely by several workers with SELECT ... FOR UPDATE SKIP LOCKED.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(f"type IN {JOB_TYPES}", name="ck_jobs_type"),
        CheckConstraint(f"status IN {JOB_STATUSES}", name="ck_jobs_status"),
    )

    type: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(12), default="queued", index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str | None] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    upload_id: Mapped[str | None] = mapped_column(
        ForeignKey("syllabus_uploads.id", ondelete="CASCADE"), index=True
    )
    # Set for plan jobs: whose study plan is being personalised.
    enrollment_id: Mapped[str | None] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    params: Mapped[dict] = mapped_column(JSONType, default=dict)
    # {"step": "Writing questions", "done": 2, "total": 6}
    progress: Mapped[dict] = mapped_column(JSONType, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONType)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
