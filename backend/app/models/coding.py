from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JSONType
from app.models.base import LEVELS, IdMixin, TimestampMixin, utcnow

LANGUAGES = ("c", "cpp", "python")
SUBMISSION_MODES = ("run", "submit", "check")  # run: sample tests; submit: all tests; check: faculty, all, full detail
SUBMISSION_STATES = ("queued", "running", "done")
VERDICTS = ("accepted", "wrong_answer", "compile_error", "runtime_error", "time_limit", "output_limit",
            "internal_error")


class CodingProblem(IdMixin, TimestampMixin, Base):
    """A LeetCode-style exercise: read stdin, write stdout, judged against stored tests."""

    __tablename__ = "coding_problems"
    __table_args__ = (CheckConstraint(f"level IN {LEVELS}", name="ck_coding_problems_level"),)

    subtopic_id: Mapped[str] = mapped_column(ForeignKey("subtopics.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(200))
    statement: Mapped[str] = mapped_column(Text, default="")  # Markdown
    level: Mapped[str] = mapped_column(String(16), default="beginner")
    languages: Mapped[list] = mapped_column(JSONType, default=list)  # subset of LANGUAGES
    starter: Mapped[dict] = mapped_column(JSONType, default=dict)  # language -> starting code
    time_limit_ms: Mapped[int] = mapped_column(Integer, default=2000)
    memory_mb: Mapped[int] = mapped_column(Integer, default=256)
    # [{"input": "3\n", "expected": "6\n", "sample": true}]. Samples are shown to students; the rest are hidden.
    tests: Mapped[list] = mapped_column(JSONType, default=list)


class CodeSubmission(IdMixin, Base):
    __tablename__ = "code_submissions"
    __table_args__ = (
        CheckConstraint(f"mode IN {SUBMISSION_MODES}", name="ck_code_submissions_mode"),
        CheckConstraint(f"state IN {SUBMISSION_STATES}", name="ck_code_submissions_state"),
    )

    problem_id: Mapped[str] = mapped_column(ForeignKey("coding_problems.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(10))
    mode: Mapped[str] = mapped_column(String(8))
    code: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(8), default="queued", index=True)
    verdict: Mapped[str | None] = mapped_column(String(16))
    passed: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    runtime_ms: Mapped[int | None] = mapped_column(Integer)
    compile_output: Mapped[str | None] = mapped_column(Text)
    # Per-test outcome, stored in full; the API removes what a student must not see.
    results: Mapped[list] = mapped_column(JSONType, default=list)
    message: Mapped[str | None] = mapped_column(String(300))  # why a run failed on our side
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
