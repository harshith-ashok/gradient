from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.learning import EnrollmentDetail, EnrollmentSummary


class StudentPublic(BaseModel):
    id: str
    name: str
    email: str
    student_id: str | None = None
    program: str | None = None
    year: str | None = None


class AdminRow(BaseModel):
    student: StudentPublic
    enrollment: EnrollmentSummary | None = None


class Kpis(BaseModel):
    students: int
    active_learners: int
    average_progress: int
    need_attention: int


class CourseStat(BaseModel):
    id: str
    code: str
    title: str
    enrolled: int
    average: int
    threshold: int


class Overview(BaseModel):
    kpis: Kpis
    courses: list[CourseStat]
    rows: list[AdminRow]
    total: int = Field(description="Rows matching the filters, before pagination")
    page: int
    page_size: int


class StudentDetailOut(BaseModel):
    student: StudentPublic
    enrollments: list[EnrollmentDetail]


class CourseSetting(BaseModel):
    id: str
    code: str
    title: str
    status: Literal["draft", "published"]
    override: int | None = None
    effective: int


class SettingsOut(BaseModel):
    global_threshold: int
    min: int
    max: int
    courses: list[CourseSetting]


class SettingsUpdate(BaseModel):
    global_threshold: int
    per_course: dict[str, int | None] = Field(
        default_factory=dict,
        description="course id → own pass mark; null or missing means use the global one",
    )
