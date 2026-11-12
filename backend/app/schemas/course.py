from typing import Literal

from pydantic import BaseModel, Field

# ---------- Student-facing (no quiz answers) ----------


class SubtopicBrief(BaseModel):
    id: str
    title: str
    description: str = ""


class TopicOut(BaseModel):
    id: str
    title: str
    subtopics: list[SubtopicBrief]


class CourseCard(BaseModel):
    id: str
    code: str
    title: str
    department: str | None = None
    credits: int | None = None
    level: str | None = None
    accent: str | None = None
    description: str = ""
    instructor: str
    threshold: int
    topic_count: int
    subtopic_count: int


class CourseStructure(CourseCard):
    topics: list[TopicOut]


class FlashcardOut(BaseModel):
    front: str
    back: str


class RemediationOut(BaseModel):
    explanation: str
    steps: list[str]


class SubtopicContent(BaseModel):
    id: str
    title: str
    description: str = ""
    points: list[str]
    summary: list[str]
    flashcards: list[FlashcardOut]
    remediation: RemediationOut | None = None


class NavLink(BaseModel):
    id: str
    title: str


class SubtopicView(BaseModel):
    course: NavLink = Field(description="id and title of the course")
    course_code: str
    topic: NavLink
    subtopic: SubtopicContent
    threshold: int
    prev: NavLink | None = None
    next: NavLink | None = None


# ---------- Staff-facing (full tree, includes answers) ----------

CourseStatus = Literal["draft", "published"]


class StaffCourseItem(BaseModel):
    id: str
    code: str
    title: str
    department: str | None = None
    status: CourseStatus
    accent: str | None = None
    source_file: str | None = None
    topic_count: int
    subtopic_count: int
    enrolled: int
    threshold: int


class QuestionEdit(BaseModel):
    id: str | None = None
    text: str
    options: list[str] = Field(min_length=2)
    answer_index: int = 0
    explanation: str = ""


class SubtopicEdit(BaseModel):
    id: str | None = None
    title: str
    description: str = ""
    points: list[str] = []
    summary: list[str] = []
    flashcards: list[FlashcardOut] = []
    questions: list[QuestionEdit] = []
    remediation: RemediationOut | None = None


class TopicEdit(BaseModel):
    id: str | None = None
    title: str
    summary: str = ""
    subtopics: list[SubtopicEdit] = []


class CourseSave(BaseModel):
    code: str
    title: str
    department: str | None = None
    credits: int | None = None
    level: str | None = None
    accent: str | None = None
    description: str = ""
    topics: list[TopicEdit] = []


class CourseFull(CourseSave):
    id: str
    status: CourseStatus
    source_file: str | None = None
    owner_id: str


class StatusChange(BaseModel):
    status: CourseStatus


class StatusOut(BaseModel):
    id: str
    status: CourseStatus
