from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, JSONType
from app.models.base import LEVELS, IdMixin, TimestampMixin, utcnow

TASK_TYPES = ("study", "quiz", "confirm", "remediation", "retake", "topic_quiz")


class Enrollment(IdMixin, TimestampMixin, Base):
    """A student's place in a course. Created when the pre-test is submitted."""

    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_enrollment"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    minutes_per_day: Mapped[int] = mapped_column(Integer, default=60)
    plan_start_date: Mapped[date] = mapped_column(Date)
    pretest_score: Mapped[float | None] = mapped_column(Float)
    pretest_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tasks: Mapped[list["PlanTask"]] = relationship(
        order_by="PlanTask.position", cascade="all, delete-orphan"
    )
    mastery: Mapped[list["Mastery"]] = relationship(cascade="all, delete-orphan")
    pretest_results: Mapped[list["PretestResult"]] = relationship(cascade="all, delete-orphan")
    notices: Mapped[list["PlanNotice"]] = relationship(
        order_by="PlanNotice.created_at, PlanNotice.id", cascade="all, delete-orphan"
    )
    day_statuses: Mapped[list["DayStatus"]] = relationship(
        order_by="DayStatus.day_index", cascade="all, delete-orphan"
    )
    attempts: Mapped[list["QuizAttempt"]] = relationship(
        order_by="QuizAttempt.created_at, QuizAttempt.id", cascade="all, delete-orphan"
    )


class PretestResult(IdMixin, Base):
    __tablename__ = "pretest_results"
    __table_args__ = (UniqueConstraint("enrollment_id", "subtopic_id", name="uq_pretest"),)

    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    subtopic_id: Mapped[str] = mapped_column(ForeignKey("subtopics.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Float)  # 0-100


class Mastery(IdMixin, Base):
    __tablename__ = "mastery"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "subtopic_id", name="uq_mastery"),
        CheckConstraint(f"level IN {LEVELS}", name="ck_mastery_level"),
    )

    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    subtopic_id: Mapped[str] = mapped_column(ForeignKey("subtopics.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Float, default=0)  # mastery value, 0-100
    level: Mapped[str] = mapped_column(String(16), default="beginner")
    last_score: Mapped[float | None] = mapped_column(Float)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    studied: Mapped[bool] = mapped_column(default=False)
    needs_review: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class PlanTask(IdMixin, TimestampMixin, Base):
    __tablename__ = "plan_tasks"
    __table_args__ = (
        CheckConstraint(f"type IN {TASK_TYPES}", name="ck_plan_tasks_type"),
        CheckConstraint("status IN ('todo', 'done')", name="ck_plan_tasks_status"),
    )

    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    subtopic_id: Mapped[str | None] = mapped_column(ForeignKey("subtopics.id", ondelete="CASCADE"))
    topic_id: Mapped[str | None] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(255), default="")
    minutes: Mapped[int] = mapped_column(Integer, default=10)
    day_index: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_for: Mapped[date] = mapped_column(Date, index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(8), default="todo")
    result: Mapped[str | None] = mapped_column(String(80))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlanNotice(IdMixin, Base):
    """Messages about plan changes, e.g. "Scored 25%... retake scheduled for Day 5"."""

    __tablename__ = "plan_notices"

    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(16))  # info | recalc | reschedule
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DayStatus(IdMixin, Base):
    """End-of-day status, e.g. "Day 3 completed – 100% mastery"."""

    __tablename__ = "day_statuses"
    __table_args__ = (UniqueConstraint("enrollment_id", "day_index", name="uq_day_status"),)

    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    day_index: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date)
    mastery: Mapped[int] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class QuizAttempt(IdMixin, Base):
    """Every quiz attempt is kept, giving students their history."""

    __tablename__ = "quiz_attempts"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('pretest', 'subtopic', 'topic', 'practice')", name="ck_attempts_kind"
        ),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(255), default="")
    subtopic_id: Mapped[str | None] = mapped_column(ForeignKey("subtopics.id", ondelete="SET NULL"))
    topic_id: Mapped[str | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    score: Mapped[float] = mapped_column(Float)  # 0-100
    correct: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    # The pass mark in force when the attempt was taken. NULL for the diagnostic pre-test.
    pass_mark: Mapped[int | None] = mapped_column(Integer)
    passed: Mapped[bool | None] = mapped_column()
    # Per-sub-topic breakdown and the questions/answers given, for review.
    breakdown: Mapped[list] = mapped_column(JSONType, default=list)
    answers: Mapped[list] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class QuizSession(IdMixin, Base):
    """An open quiz. Holds the shuffled questions and answer key until the quiz is submitted."""

    __tablename__ = "quiz_sessions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(10))
    topic_id: Mapped[str | None] = mapped_column(String(40))
    subtopic_id: Mapped[str | None] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(255))
    scope: Mapped[str] = mapped_column(String(255), default="")
    questions: Mapped[list] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
