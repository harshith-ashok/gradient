"""Study-plan agent: decides how long to spend on each sub-topic, in what order, and at what level.

The model only proposes. `validate` throws away anything that does not make sense, and the plan
service then fits the result into the student's time frame, so a bad answer can only make the plan
less tailored, never leave part of the syllabus uncovered.
"""

from app.agents.llm import LLM
from app.agents.prompts import PLAN_SYSTEM, plan_prompt
from app.agents.schemas import PlanProposal
from app.models.base import LEVELS


def propose(llm: LLM, *, course: str, pass_mark: int, days_left: int, minutes_per_day: int,
            study_budget: int, rows: list[str], reason: str) -> PlanProposal:
    prompt = plan_prompt(course, pass_mark, days_left, minutes_per_day, study_budget, rows, reason)
    return llm.structured(PLAN_SYSTEM, prompt, PlanProposal, think="low", temperature=0.2)


def allowed_levels(score: float, pass_mark: int) -> tuple[str, ...]:
    """Levels the model may start a sub-topic at, from that sub-topic's pre-test score."""
    if score >= pass_mark:
        return ("intermediate", "advanced")
    if score >= pass_mark / 2:
        return ("beginner", "intermediate")
    return ("beginner",)


def validate(p: PlanProposal, known: set[str]) -> dict[str, dict]:
    """Per sub-topic: {"minutes", "priority", "level", "focus"}. Unknown ids and repeats are dropped."""
    out: dict[str, dict] = {}
    for it in p.items:
        if it.subtopic_id in known and it.subtopic_id not in out:
            out[it.subtopic_id] = {"minutes": it.study_minutes, "priority": it.priority,
                                   "level": it.start_level if it.start_level in LEVELS else "beginner",
                                   "focus": it.focus.strip()}
    return out
