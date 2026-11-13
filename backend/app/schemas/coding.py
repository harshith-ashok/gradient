from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Language = Literal["c", "cpp", "python"]
Level = Literal["beginner", "intermediate", "advanced", "expert"]
Verdict = Literal["accepted", "wrong_answer", "compile_error", "runtime_error", "time_limit", "output_limit",
                  "internal_error"]
MAX_TEST_TEXT = 20_000


class TestCase(BaseModel):
    __test__ = False  # not a pytest class

    input: str = Field(max_length=MAX_TEST_TEXT)
    expected: str = Field(max_length=MAX_TEST_TEXT)
    sample: bool = Field(False, description="Shown to students; the others stay hidden")


class ProblemIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    statement: str = Field(max_length=20_000)
    level: Level = "beginner"
    languages: list[Language] = Field(min_length=1)
    starter: dict[Language, str] = Field(default_factory=dict)
    time_limit_ms: int = Field(2000, ge=200, le=5000)
    memory_mb: int = Field(256, ge=32, le=512)
    tests: list[TestCase] = Field(min_length=1, max_length=40)

    @field_validator("languages")
    @classmethod
    def _unique(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))

    @field_validator("starter")
    @classmethod
    def _starter_size(cls, v: dict) -> dict:
        if any(len(code) > 20_000 for code in v.values()):
            raise ValueError("starter code is too long")
        return v


class ProblemFull(ProblemIn):
    id: str
    subtopic_id: str
    position: int


# ---------------------------------------------------------------- students
class ProblemBrief(BaseModel):
    id: str
    title: str
    level: Level
    languages: list[Language]
    solved: bool
    attempts: int


class Sample(BaseModel):
    input: str
    expected: str


class ProblemDetail(BaseModel):
    id: str
    title: str
    statement: str
    level: Level
    languages: list[Language]
    starter: dict[str, str]
    time_limit_ms: int
    memory_mb: int
    samples: list[Sample]
    hidden_tests: int
    solved: bool
    subtopic_id: str
    subtopic_title: str
    course_id: str
    course_code: str
    course_title: str


class SubmitRequest(BaseModel):
    language: Language
    code: str = Field(min_length=1)
    mode: Literal["run", "submit"] = Field("run", description="run: sample tests only; submit: all tests")


class StaffRunRequest(BaseModel):
    language: Language
    code: str = Field(min_length=1)


class SubmissionCreated(BaseModel):
    id: str


class TestResult(BaseModel):
    __test__ = False

    index: int
    sample: bool
    verdict: Literal["ok", "wrong_answer", "runtime_error", "time_limit", "output_limit", "skipped"]
    ms: int
    input: str | None = None
    expected: str | None = None
    stdout: str | None = None
    stderr: str | None = None


class SubmissionOut(BaseModel):
    id: str
    problem_id: str
    language: Language
    mode: Literal["run", "submit", "check"]
    state: Literal["queued", "running", "done"]
    verdict: Verdict | None = None
    passed: int
    total: int
    runtime_ms: int | None = None
    compile_output: str | None = None
    message: str | None = None
    results: list[TestResult]
    code: str
    created_at: datetime
    queue_position: int | None = Field(None, description="Submissions ahead of this one while it waits")


class SubmissionBrief(BaseModel):
    id: str
    language: Language
    mode: Literal["run", "submit", "check"]
    state: Literal["queued", "running", "done"]
    verdict: Verdict | None = None
    passed: int
    total: int
    created_at: datetime
