from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, JSONType
from app.models.base import LEVELS, IdMixin, TimestampMixin


class Course(IdMixin, TimestampMixin, Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published')", name="ck_courses_status"),
    )

    code: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(120))
    credits: Mapped[int | None] = mapped_column(Integer)
    level_label: Mapped[str | None] = mapped_column(String(120))
    accent: Mapped[str | None] = mapped_column(String(9))
    description: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(12), default="draft", index=True)
    # Per-course override of the global pass mark (0-100). NULL means use the global one.
    pass_mark: Mapped[int | None] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255))

    topics: Mapped[list["Topic"]] = relationship(
        back_populates="course", order_by="Topic.position", cascade="all, delete-orphan"
    )


class Topic(IdMixin, Base):
    __tablename__ = "topics"

    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")

    course: Mapped[Course] = relationship(back_populates="topics")
    subtopics: Mapped[list["Subtopic"]] = relationship(
        back_populates="topic", order_by="Subtopic.position", cascade="all, delete-orphan"
    )


class Subtopic(IdMixin, Base):
    __tablename__ = "subtopics"

    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    key_points: Mapped[list] = mapped_column(JSONType, default=list)
    # Summary paragraphs, in order.
    summary: Mapped[list] = mapped_column(JSONType, default=list)

    topic: Mapped[Topic] = relationship(back_populates="subtopics")
    flashcards: Mapped[list["Flashcard"]] = relationship(
        order_by="Flashcard.position", cascade="all, delete-orphan"
    )
    questions: Mapped[list["Question"]] = relationship(
        order_by="Question.position", cascade="all, delete-orphan"
    )
    remediation: Mapped[list["RemediationItem"]] = relationship(cascade="all, delete-orphan")


class Flashcard(IdMixin, Base):
    __tablename__ = "flashcards"

    subtopic_id: Mapped[str] = mapped_column(
        ForeignKey("subtopics.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(16), default="beginner")
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)


class Question(IdMixin, Base):
    __tablename__ = "questions"
    __table_args__ = (CheckConstraint(f"level IN {LEVELS}", name="ck_questions_level"),)

    subtopic_id: Mapped[str] = mapped_column(
        ForeignKey("subtopics.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(16), default="beginner")
    type: Mapped[str] = mapped_column(String(16), default="mcq")
    text: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSONType)
    # Index into `options` of the correct answer.
    answer_index: Mapped[int] = mapped_column(Integer, default=0)
    explanation: Mapped[str] = mapped_column(Text, default="")


class RemediationItem(IdMixin, Base):
    __tablename__ = "remediation_items"

    subtopic_id: Mapped[str] = mapped_column(
        ForeignKey("subtopics.id", ondelete="CASCADE"), index=True
    )
    explanation: Mapped[str] = mapped_column(Text)
    steps: Mapped[list] = mapped_column(JSONType, default=list)


class SyllabusUpload(IdMixin, TimestampMixin, Base):
    """A syllabus file or pasted text, and the state of the agent run that reads it."""

    __tablename__ = "syllabus_uploads"

    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_ref: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(16), default="uploaded")
    extracted_text: Mapped[str | None] = mapped_column(Text)
    agent_run_id: Mapped[str | None] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(Text)
