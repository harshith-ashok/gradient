"""Study-material agent (LangGraph), one sub-topic at a time:

    retrieve → material → summaries → questions → verify ─┬─► done
                                          ▲               │ some level short of questions (and tries left)
                                          └───────────────┘

`material` writes flashcards (per level) and remediation. `summaries` writes one summary per level,
so each student reads the one matching their level for this sub-topic. `questions` writes multiple
choice questions per level; deterministic checks drop malformed ones. `verify` has the model answer
every question blind (it never sees the key) and drops any it answers differently, which catches
wrong answer keys. Levels that end up with too few questions are retried, then reported.
"""

import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents import prompts
from app.agents.llm import LLM, LLMError
from app.agents.retrieval import retrieve
from app.agents.schemas import BlindAnswers, LeveledSummaries, MaterialDraft, QuestionDraft, QuestionSet
from app.agents.validation import (
    MIN_QUESTIONS_PER_LEVEL,
    material_problems,
    norm,
    summaries_problems,
    valid_questions,
)
from app.agents.vectorstore import VectorStore

log = logging.getLogger(__name__)
QUESTIONS_PER_LEVEL = 4
MAX_PER_LEVEL = 5
MAX_ROUNDS = 2


class ContentState(TypedDict, total=False):
    # inputs
    course_id: str
    syllabus_text: str
    topic: str
    subtopic: str
    description: str
    points: list[str]
    levels: list[str]  # levels to generate questions for
    flashcard_levels: list[str]
    want_material: bool
    summary_levels: list[str]  # levels to write a summary for (may be empty)
    existing_stems: list[str]
    verify: bool
    # working
    context: str
    material: MaterialDraft | None
    summaries: dict[str, list[str]]
    questions: dict[str, list[QuestionDraft]]  # verified survivors per level
    pending: list[tuple[str, QuestionDraft]]  # new questions awaiting verification
    need: list[str]
    rounds: int
    warnings: list[str]


def generate_content(llm: LLM, store: VectorStore, state: ContentState) -> ContentState:
    taken: set[str] = {norm(s) for s in state.get("existing_stems", [])}
    verify_on = state.get("verify", True)

    def retrieve_node(s: ContentState) -> ContentState:
        query = f"{s['topic']} {s['subtopic']} {' '.join(s['points'])}"
        context = retrieve(llm, store, s["course_id"], s["syllabus_text"], query)[:8000]
        return {"context": context, "need": list(s["levels"]), "questions": {}, "pending": [], "rounds": 0,
                "warnings": [], "material": None, "summaries": {}}

    def material_node(s: ContentState) -> ContentState:
        if not s.get("want_material"):
            return {}
        problems: list[str] = []
        for _ in range(2):
            m = llm.structured(
                prompts.SYSTEM,
                prompts.material_prompt(s["topic"], s["subtopic"], s["description"], s["points"], s["context"],
                                        s["flashcard_levels"], problems),
                MaterialDraft,
            )
            problems = material_problems(m, s["flashcard_levels"])
            if not problems:
                return {"material": m}
        raise LLMError(f"Study material for “{s['subtopic']}” failed checks: {'; '.join(problems)}")

    def summaries_node(s: ContentState) -> ContentState:
        levels = s.get("summary_levels") or []
        if not levels:
            return {}
        problems: list[str] = []
        for _ in range(2):
            out = llm.structured(
                prompts.SYSTEM,
                prompts.summaries_prompt(s["topic"], s["subtopic"], s["description"], s["points"], s["context"],
                                         levels, problems),
                LeveledSummaries,
            )
            problems = summaries_problems(out, levels)
            if not problems:
                return {"summaries": {x.level: [p.strip() for p in x.paragraphs] for x in out.summaries
                                      if x.level in levels}}
        raise LLMError(f"Summaries for “{s['subtopic']}” failed checks: {'; '.join(problems)}")

    def questions_node(s: ContentState) -> ContentState:
        """Write questions for each level still short. New ones wait in `pending` to be verified."""
        pending: list[tuple[str, QuestionDraft]] = []
        for level in s["need"]:
            have = [q.text for qs in s["questions"].values() for q in qs]
            known = have + [q.text for _, q in pending] + list(s.get("existing_stems", []))
            qs = llm.structured(
                prompts.SYSTEM,
                prompts.questions_prompt(s["topic"], s["subtopic"], s["points"], s["context"], level,
                                         QUESTIONS_PER_LEVEL, known, []),
                QuestionSet, think="medium",
            )
            pending += [(level, q) for q in valid_questions(qs.questions, taken)]
        return {"pending": pending, "rounds": s["rounds"] + 1}

    def verify_node(s: ContentState) -> ContentState:
        """Blind check: the model answers each new question without seeing the key."""
        pending = s["pending"]
        warnings = list(s.get("warnings", []))
        bad: set[int] = set()
        if verify_on and pending:
            numbered = "\n\n".join(
                f"Question {i}: {q.text}\n" + "\n".join(f"  {j}. {o}" for j, o in enumerate(q.options))
                for i, (_, q) in enumerate(pending, 1)
            )
            try:
                result = llm.structured(
                    prompts.SYSTEM, prompts.verify_prompt(s["context"], numbered), BlindAnswers, think="medium"
                )
                picks = {a.question_number: a.chosen_index for a in result.answers}
                bad = {i for i, (_, q) in enumerate(pending, 1) if i in picks and picks[i] != q.answer_index}
                if bad:
                    warnings.append(f"{len(bad)} question(s) dropped: the checker disagreed with the answer key")
            except LLMError as e:
                warnings.append(f"verification skipped: {e}")
        got = {k: list(v) for k, v in s["questions"].items()}
        for i, (level, q) in enumerate(pending, 1):
            if i not in bad:
                got.setdefault(level, []).append(q)
        got = {k: v[:MAX_PER_LEVEL] for k, v in got.items()}
        need = [lvl for lvl in s["levels"] if len(got.get(lvl, [])) < MIN_QUESTIONS_PER_LEVEL]
        return {"questions": got, "pending": [], "need": need, "warnings": warnings}

    def after_verify(s: ContentState) -> str:
        return "questions" if s["need"] and s["rounds"] < MAX_ROUNDS else END

    g = StateGraph(ContentState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("material", material_node)
    g.add_node("summaries", summaries_node)
    g.add_node("questions", questions_node)
    g.add_node("verify", verify_node)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "material")
    g.add_edge("material", "summaries")
    g.add_edge("summaries", "questions")
    g.add_edge("questions", "verify")
    g.add_conditional_edges("verify", after_verify, {"questions": "questions", END: END})
    out = g.compile().invoke(state)

    short = [lvl for lvl in state["levels"] if len(out["questions"].get(lvl, [])) < MIN_QUESTIONS_PER_LEVEL]
    warnings = list(out.get("warnings", []))
    if short:
        warnings.append(f"not enough valid questions for: {', '.join(short)}")
    out["questions"] = {k: v for k, v in out["questions"].items() if len(v) >= MIN_QUESTIONS_PER_LEVEL}
    out["warnings"] = warnings
    return out
