from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.course import CourseCard, CourseStructure, SubtopicView

Level = Literal["beginner", "intermediate", "advanced", "expert"]
TaskType = Literal["study", "quiz", "confirm", "remediation", "retake", "topic_quiz"]
SubStatus = Literal["new", "learning", "review", "mastered"]
EnrStatus = Literal["on-track", "attention", "completed"]
QuizKind = Literal["pretest", "topic", "subtopic", "practice"]


class TaskOut(BaseModel):
    id: str
    type: TaskType
    topic_id: str | None = None
    subtopic_id: str | None = None
    title: str
    minutes: int
    day: int = Field(description="0-based plan day")
    date: date
    done: bool
    done_at: datetime | None = None
    result: str | None = None
    note: str | None = Field(default=None, description="Why the planner put this here")


class DayStatusOut(BaseModel):
    id: str
    day_index: int
    day: int = Field(description="1-based day number")
    date: date
    mastery: int
    message: str
    created_at: datetime


class NoticeOut(BaseModel):
    id: str
    kind: Literal["info", "recalc", "reschedule"]
    text: str
    created_at: datetime


class TopicMastery(BaseModel):
    id: str
    title: str
    mastery: int


class UpcomingTask(BaseModel):
    id: str
    title: str
    type: TaskType
    date: date
    minutes: int


class AttemptOut(BaseModel):
    id: str
    kind: QuizKind
    title: str
    score: float
    correct: int
    total: int
    passed: bool | None = None
    threshold: int | None = None
    created_at: datetime
    course_id: str | None = None


class SubtopicProgress(BaseModel):
    id: str
    title: str
    mastery: int
    last_score: float | None = None
    attempts: int
    status: SubStatus
    level: Level


class TopicDetail(BaseModel):
    id: str
    title: str
    mastery: int
    subtopics: list[SubtopicProgress]


class PretestSub(BaseModel):
    subtopic_id: str
    title: str
    score: float


class PretestInfo(BaseModel):
    taken_at: datetime | None = None
    score: float | None = None
    by_subtopic: list[PretestSub]


class EnrollmentSummary(BaseModel):
    enrollment_id: str
    course_id: str
    code: str
    title: str
    accent: str | None = None
    overall: int
    threshold: int
    topics: list[TopicMastery]
    upcoming: list[UpcomingTask]
    pending_count: int
    today_tasks: list[TaskOut]
    plan_done: int
    plan_total: int
    remediation_count: int
    attempts: int
    last_activity: datetime
    pretest_score: float | None = None
    latest_day_status: DayStatusOut | None = None
    status: EnrStatus
    day_number: int
    today: date = Field(description="Today's date in the plan's calendar (server timezone)")


class PlanWindow(BaseModel):
    target_days: int
    ends_on: date = Field(description="Last day of the time frame")
    fits: bool = Field(description="Whether everything left is scheduled inside the time frame")
    finish_date: date | None = Field(default=None, description="When the last task is scheduled")
    needed_minutes_per_day: int = Field(description="Least daily time that still covers everything left")


class EnrollmentDetail(EnrollmentSummary):
    start_date: date
    minutes_per_day: int
    target_days: int
    plan_window: PlanWindow
    planning: bool = Field(description="True while the AI planner is still personalising the plan")
    notices: list[NoticeOut]
    tasks: list[TaskOut]
    day_statuses: list[DayStatusOut]
    pretest: PretestInfo
    topic_detail: list[TopicDetail]
    history: list[AttemptOut]


# ---- course pages with the student's own data ----


class CatalogItem(CourseCard):
    enrollment: EnrollmentSummary | None = None


class StudentCourse(CourseStructure):
    enrollment: EnrollmentDetail | None = None


class MasteryOut(BaseModel):
    value: int
    last_score: float | None = None
    attempts: int
    remediation: bool
    studied: bool
    level: Level
    status: SubStatus


class StudentSubtopicView(SubtopicView):
    mastery: MasteryOut | None = None
    tasks: list[TaskOut] = []


# ---- quizzes ----


class QuizStartRequest(BaseModel):
    course_id: str
    kind: QuizKind
    topic_id: str | None = None
    subtopic_id: str | None = None


class QuizQuestion(BaseModel):
    id: str
    text: str
    options: list[str]


class QuizStart(BaseModel):
    quiz_id: str
    kind: QuizKind
    course_id: str
    title: str
    scope: str
    threshold: int | None = Field(description="Pass mark; null for the diagnostic pre-test")
    questions: list[QuizQuestion]


class QuizSubmitRequest(BaseModel):
    answers: dict[str, int] = Field(description="question id → index of the chosen option")


class ReviewItem(BaseModel):
    id: str
    text: str
    options: list[str]
    chosen: int | None = None
    answer: int
    correct: bool
    explanation: str
    subtopic_title: str


class SubtopicResult(BaseModel):
    subtopic_id: str
    title: str
    score: float
    correct: int
    total: int
    before: float | None = None
    after: float
    level: Level
    promoted: bool


class FollowUp(BaseModel):
    title: str
    type: TaskType
    date: date
    day: int


class Actions(BaseModel):
    failed: bool
    items: list[FollowUp]
    shifted: int


class NextTask(BaseModel):
    id: str
    title: str
    type: TaskType
    date: date
    subtopic_id: str | None = None
    topic_id: str | None = None


class PlanCreated(BaseModel):
    days: int
    tasks: int
    minutes_per_day: int


class QuizResult(BaseModel):
    kind: QuizKind
    course_id: str
    title: str
    score: float
    correct: int
    total: int
    passed: bool | None = None
    threshold: int
    review: list[ReviewItem]
    by_subtopic: list[SubtopicResult]
    actions: Actions | None = None
    day_status: DayStatusOut | None = None
    next_task: NextTask | None = None
    plan: PlanCreated | None = None


# ---- tasks / plan ----


class CompleteSubtopicRequest(BaseModel):
    type: Literal["study", "remediation"]


class CompleteResult(BaseModel):
    task_id: str | None = None
    day_status: DayStatusOut | None = None


class PlanMinutesRequest(BaseModel):
    minutes_per_day: int | None = None
    target_days: int | None = Field(default=None, description="Days allowed to finish the course")


# ---- dashboard / progress / practice ----


class TodayTask(TaskOut):
    course_id: str
    course_code: str
    course_title: str


class StatusWithCourse(DayStatusOut):
    course_id: str
    course_code: str


class Dashboard(BaseModel):
    enrollments: list[EnrollmentSummary]
    today: list[TodayTask]
    statuses: list[StatusWithCourse]
    recent: list[AttemptOut]


class Progress(BaseModel):
    enrollments: list[EnrollmentDetail]


class PracticeSub(BaseModel):
    id: str
    title: str
    topic: str
    mastery: int
    status: SubStatus


class PracticeCourse(BaseModel):
    course_id: str
    code: str
    title: str
    subtopics: list[PracticeSub]


class BreakdownItem(BaseModel):
    subtopic_id: str
    title: str
    score: float
    correct: int
    total: int


class AttemptDetail(AttemptOut):
    breakdown: list[BreakdownItem]


class CourseHistory(BaseModel):
    course_id: str
    code: str
    title: str
    attempts: list[AttemptDetail]
