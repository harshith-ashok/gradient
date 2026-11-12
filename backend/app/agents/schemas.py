"""Shapes the model must return. Constraints here become the JSON schema sent to the model and
the validation applied to what comes back (violations trigger one repair attempt)."""

from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["beginner", "intermediate", "advanced", "expert"]


class TopicDraft(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    summary: str = Field(min_length=10, max_length=400, description="One or two sentences")


class TopicList(BaseModel):
    topics: list[TopicDraft] = Field(min_length=1, max_length=30)


class SubtopicDraft(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=10, max_length=300, description="One sentence")
    key_points: list[str] = Field(min_length=2, max_length=8, description="Short factual statements")


class SubtopicList(BaseModel):
    subtopics: list[SubtopicDraft] = Field(min_length=2, max_length=8)


class FlashcardDraft(BaseModel):
    level: Level
    front: str = Field(min_length=5, max_length=300)
    back: str = Field(min_length=3, max_length=500)


class RemediationDraft(BaseModel):
    explanation: str = Field(min_length=40, max_length=1200)
    steps: list[str] = Field(min_length=2, max_length=6)


class LevelSummary(BaseModel):
    level: Level
    paragraphs: list[str] = Field(
        min_length=1, max_length=4,
        description="2 or 3 separate paragraphs, each a distinct step of the explanation (one item per paragraph)",
    )


class LeveledSummaries(BaseModel):
    summaries: list[LevelSummary] = Field(min_length=1, max_length=4)


class MaterialDraft(BaseModel):
    flashcards: list[FlashcardDraft] = Field(min_length=2, max_length=24)  # per-level minimum is checked separately
    remediation: RemediationDraft


class QuestionDraft(BaseModel):
    text: str = Field(min_length=10, max_length=500)
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3, description="Index of the correct option")
    explanation: str = Field(min_length=10, max_length=600)


class QuestionSet(BaseModel):
    questions: list[QuestionDraft] = Field(min_length=3, max_length=8)


class PickedAnswer(BaseModel):
    question_number: int = Field(ge=1)
    chosen_index: int = Field(ge=0, le=3)


class BlindAnswers(BaseModel):
    answers: list[PickedAnswer]


class SubPlan(BaseModel):
    subtopic_id: str = Field(description="Copy the id exactly as given")
    study_minutes: int = Field(ge=10, le=90, description="Minutes of study this sub-topic needs")
    priority: int = Field(ge=1, le=60, description="1 is studied first within its topic")
    start_level: Level = Field(description="Level to start this sub-topic at")
    focus: str = Field(min_length=5, max_length=200,
                       description="One sentence telling the student what to concentrate on")


class PlanProposal(BaseModel):
    summary: str = Field(min_length=10, max_length=400, description="Two sentences on how the plan was shaped")
    items: list[SubPlan] = Field(min_length=1, max_length=200)
