"""Syllabus agents (LangGraph): topics from the whole syllabus, then sub-topics for chosen topics.

Each graph is generate → check → (repair and retry once). Retries add the specific problems found to
the prompt, so the model fixes them instead of re-rolling blindly."""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents import prompts
from app.agents.llm import LLM, LLMError
from app.agents.schemas import SubtopicDraft, SubtopicList, TopicDraft, TopicList
from app.agents.validation import clean_subtopics, clean_topics

MAX_PROMPT_CHARS = 60_000
MAX_TRIES = 2


class _TopicsState(TypedDict, total=False):
    text: str
    topics: list[TopicDraft]
    problems: list[str]
    tries: int


def analyze_topics(llm: LLM, text: str) -> list[TopicDraft]:
    def generate(s: _TopicsState) -> _TopicsState:
        out = llm.structured(prompts.SYSTEM, prompts.topics_prompt(s["text"], s.get("problems", [])), TopicList)
        return {"topics": out.topics, "tries": s.get("tries", 0) + 1}

    def check(s: _TopicsState) -> _TopicsState:
        topics = clean_topics(s["topics"])
        problems = [] if topics else ["no usable topics"]
        if len(topics) < len(s["topics"]):
            problems.append("topic titles must all be different")
        return {"topics": topics, "problems": problems if len(topics) < 1 else []}

    g = StateGraph(_TopicsState)
    g.add_node("generate", generate)
    g.add_node("check", check)
    g.set_entry_point("generate")
    g.add_edge("generate", "check")
    g.add_conditional_edges(
        "check", lambda s: "generate" if s["problems"] and s["tries"] < MAX_TRIES else END,
        {"generate": "generate", END: END},
    )
    out = g.compile().invoke({"text": text[:MAX_PROMPT_CHARS]})
    if not out["topics"]:
        raise LLMError("No topics could be found in this syllabus.")
    return out["topics"]


class _SubState(TypedDict, total=False):
    topic: str
    summary: str
    context: str
    subtopics: list[SubtopicDraft]
    problems: list[str]
    tries: int


def derive_subtopics(llm: LLM, topic: str, summary: str, context: str) -> list[SubtopicDraft]:
    def generate(s: _SubState) -> _SubState:
        out = llm.structured(
            prompts.SYSTEM,
            prompts.subtopics_prompt(s["topic"], s["summary"], s["context"], s.get("problems", [])),
            SubtopicList,
        )
        return {"subtopics": out.subtopics, "tries": s.get("tries", 0) + 1}

    def check(s: _SubState) -> _SubState:
        subs = clean_subtopics(s["subtopics"])
        problems = []
        if len(subs) < 2:
            problems.append("need at least 2 different sub-topics, each with at least 2 key points")
        return {"subtopics": subs, "problems": problems}

    g = StateGraph(_SubState)
    g.add_node("generate", generate)
    g.add_node("check", check)
    g.set_entry_point("generate")
    g.add_edge("generate", "check")
    g.add_conditional_edges(
        "check", lambda s: "generate" if s["problems"] and s["tries"] < MAX_TRIES else END,
        {"generate": "generate", END: END},
    )
    out = g.compile().invoke({"topic": topic, "summary": summary, "context": context})
    if len(out["subtopics"]) < 2:
        raise LLMError(f"Could not derive sub-topics for “{topic}”.")
    return out["subtopics"]
