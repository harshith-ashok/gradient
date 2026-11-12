from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.course import CourseStatus  # noqa: F401  (re-exported for convenience)

Level = Literal["beginner", "intermediate", "advanced", "expert"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]


class JobOut(BaseModel):
    id: str
    type: Literal["analyze", "derive", "generate", "plan"]
    status: JobStatus
    course_id: str | None = None
    upload_id: str | None = None
    progress: dict[str, Any] = {}
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TopicOut(BaseModel):
    title: str
    summary: str


class UploadOut(BaseModel):
    id: str
    course_id: str
    file_name: str | None = None
    status: Literal["uploaded", "analyzing", "topics_ready", "deriving", "derived", "failed"]
    ocr_used: bool
    indexed: bool
    characters: int
    topics: list[TopicOut] | None = None
    error: str | None = None
    job: JobOut | None = Field(default=None, description="The most recent job for this upload")


class UploadCreated(BaseModel):
    course_id: str
    upload_id: str
    job_id: str


class DeriveRequest(BaseModel):
    topics: list[str] = Field(min_length=1, description="Titles of the topics to expand into sub-topics")
    replace: bool = Field(False, description="Rebuild topics that already exist (discards their content)")


class GenerateRequest(BaseModel):
    subtopic_ids: list[str] | None = Field(None, description="Default: every sub-topic in the course")
    levels: list[Level] | None = Field(None, description="Default: all four levels")
    force: bool = Field(False, description="Regenerate even where content already exists")


class JobQueued(BaseModel):
    job_id: str


class ModelStatus(BaseModel):
    name: str
    available: bool


class AIHealth(BaseModel):
    ok: bool
    provider: str | None = None
    url: str | None = None
    error: str | None = None
    text_model: ModelStatus | None = None
    vision_model: ModelStatus | None = None
    embed_model: ModelStatus | None = None
