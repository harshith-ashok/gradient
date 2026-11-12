"""Deterministic checks on model output. These catch what the JSON schema cannot: duplicates,
leaked answers, repeated options. Invalid items are dropped; the graph retries if too few remain."""

import re

from app.agents.schemas import LeveledSummaries, MaterialDraft, QuestionDraft, SubtopicDraft, TopicDraft

MIN_QUESTIONS_PER_LEVEL = 3


def norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def clean_topics(topics: list[TopicDraft]) -> list[TopicDraft]:
    seen, out = set(), []
    for t in topics:
        key = norm(t.title)
        if key and key not in seen:
            seen.add(key)
            out.append(TopicDraft(title=t.title.strip(), summary=t.summary.strip()))
    return out


def clean_subtopics(subs: list[SubtopicDraft]) -> list[SubtopicDraft]:
    seen, out = set(), []
    for s in subs:
        key = norm(s.title)
        points = list(dict.fromkeys(p.strip() for p in s.key_points if p.strip()))
        if key and key not in seen and len(points) >= 2:
            seen.add(key)
            out.append(SubtopicDraft(title=s.title.strip(), description=s.description.strip(), key_points=points))
    return out


def material_problems(m: MaterialDraft, levels: list[str]) -> list[str]:
    problems = []
    fronts = [norm(c.front) for c in m.flashcards]
    if len(set(fronts)) != len(fronts):
        problems.append("flashcard prompts must all be different")
    for level in levels:
        if sum(1 for c in m.flashcards if c.level == level) < 2:
            problems.append(f"need at least 2 flashcards at level '{level}'")
    return problems


def summaries_problems(out: LeveledSummaries, levels: list[str]) -> list[str]:
    """Each requested level present exactly once, substantial, and different from the others."""
    problems = []
    by_level = {}
    for s in out.summaries:
        by_level.setdefault(s.level, []).append(s)
    for level in levels:
        got = by_level.get(level, [])
        if len(got) != 1:
            problems.append(f"write exactly one summary for level '{level}'")
        elif any(len(p.strip()) < 40 for p in got[0].paragraphs):
            problems.append(f"every paragraph of the '{level}' summary must be at least 40 characters")
    texts = [norm(" ".join(by_level[lv][0].paragraphs)) for lv in levels if len(by_level.get(lv, [])) == 1]
    if len(set(texts)) != len(texts):
        problems.append("the summaries for different levels must not be identical")
    return problems


def valid_questions(qs: list[QuestionDraft], taken: set[str]) -> list[QuestionDraft]:
    """Keep well-formed questions. `taken` holds normalised stems already used in this sub-topic;
    kept stems are added to it so later levels cannot repeat them."""
    out = []
    for q in qs:
        stem = norm(q.text)
        opts = [norm(o) for o in q.options]
        if not stem or stem in taken:
            continue
        if any(not o for o in opts) or len(set(opts)) != 4:
            continue  # empty or repeated options make a question ambiguous
        correct = opts[q.answer_index]
        if len(correct) > 6 and correct in stem:
            continue  # the stem gives the answer away
        if any(o in ("all of the above", "none of the above") for o in opts):
            continue  # position-dependent, and shuffling breaks them
        taken.add(stem)
        out.append(q)
    return out
