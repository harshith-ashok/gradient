"""Job handlers: what the worker actually does. Each takes (db, job) and returns a result dict.

  analyze   read the file (OCR if scanned), index it, find topics         → upload.topics
  derive    sub-topics for the topics faculty chose                       → course tree
  generate  per-level summaries, flashcards, questions, remediation       → course content

Work is committed per topic / sub-topic, so a failure part-way keeps what was done and the result
lists what failed.
"""

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.content import generate_content
from app.agents.ingest import IngestError, extract_text
from app.agents.llm import LLM, LLMError, get_llm
from app.agents.retrieval import index_syllabus, retrieve
from app.agents.syllabus import analyze_topics, derive_subtopics
from app.agents.validation import MIN_QUESTIONS_PER_LEVEL, norm
from app.agents.vectorstore import VectorStore, collection_name, get_store
from app.core.config import get_settings
from app.models import Flashcard, Job, Question, RemediationItem, Subtopic, SyllabusUpload, Topic
from app.models.base import LEVELS, new_id
from app.repos import courses as course_repo
from app.services.jobs import UserFacingError, set_progress

log = logging.getLogger(__name__)
NO_CONTEXT = "(no syllabus excerpt is available; rely on the key points)"


def _upload(db: Session, job: Job) -> SyllabusUpload:
    up = db.get(SyllabusUpload, job.upload_id) if job.upload_id else None
    if up is None:
        raise UserFacingError("This upload no longer exists.")
    return up


def upload_path(up: SyllabusUpload) -> Path:
    return Path(get_settings().upload_dir) / (up.file_ref or "")


# ------------------------------------------------------------------ analyze


def handle_analyze(db: Session, job: Job, llm: LLM | None = None, store: VectorStore | None = None) -> dict:
    llm, store = llm or get_llm(), store or get_store()
    up = _upload(db, job)
    up.status, up.error = "analyzing", None
    set_progress(db, job, "Reading the syllabus")
    try:
        if not up.extracted_text:  # pasted text arrives already extracted
            path = upload_path(up)
            if not path.is_file():
                raise UserFacingError("The uploaded file is missing. Please upload it again.")
            out = extract_text(llm, path.read_bytes(), up.file_name or "")
            up.extracted_text, up.ocr_used = out["text"], out["ocr_used"]
            db.commit()
        set_progress(db, job, "Indexing the syllabus")
        up.indexed = index_syllabus(llm, store, up.course_id, up.extracted_text)
        db.commit()
        set_progress(db, job, "Finding the course topics")
        topics = analyze_topics(llm, up.extracted_text)
        up.topics = [{"title": t.title, "summary": t.summary} for t in topics]
        up.status = "topics_ready"
        db.commit()
    except Exception as e:
        db.rollback()
        up = db.get(SyllabusUpload, up.id)
        shown = isinstance(e, (UserFacingError, IngestError, LLMError))  # only these messages are safe to show
        up.status, up.error = "failed", str(e) if shown else None
        db.commit()
        raise
    return {"topics": len(topics), "ocr_used": up.ocr_used, "indexed": up.indexed,
            "characters": len(up.extracted_text)}


# ------------------------------------------------------------------- derive


def handle_derive(db: Session, job: Job, llm: LLM | None = None, store: VectorStore | None = None) -> dict:
    llm, store = llm or get_llm(), store or get_store()
    up = _upload(db, job)
    wanted = {norm(t) for t in job.params.get("topics", [])}
    replace = bool(job.params.get("replace", False))
    chosen = [t for t in (up.topics or []) if norm(t["title"]) in wanted]
    if not chosen:
        raise UserFacingError("None of the selected topics were found in this syllabus.")
    course = course_repo.get_with_tree(db, up.course_id)
    up.status = "deriving"
    db.commit()

    created, skipped, errors = 0, [], []
    for i, t in enumerate(chosen, 1):
        set_progress(db, job, f"Breaking down “{t['title']}”", i - 1, len(chosen))
        existing = next((x for x in course.topics if norm(x.title) == norm(t["title"])), None)
        if existing and not replace:
            skipped.append(t["title"])
            continue
        try:
            ctx = retrieve(llm, store, course.id, up.extracted_text or "", f"{t['title']} {t['summary']}")
            subs = derive_subtopics(llm, t["title"], t["summary"], ctx or NO_CONTEXT)
        except LLMError as e:
            errors.append({"topic": t["title"], "error": str(e)})
            continue
        if existing:
            course.topics.remove(existing)
            db.flush()
        topic = Topic(id=new_id(), position=len(course.topics) + 1, title=t["title"], summary=t["summary"])
        topic.subtopics = [
            Subtopic(id=new_id(), position=n, title=s.title, description=s.description,
                     key_points=s.key_points, summary=[])
            for n, s in enumerate(subs, 1)
        ]
        course.topics.append(topic)
        db.commit()
        created += 1
    if errors and not created and not skipped:
        raise UserFacingError(f"Could not break down any topic: {errors[0]['error']}")
    up.status = "derived"
    db.commit()
    set_progress(db, job, "Done", len(chosen), len(chosen))
    return {"topics_created": created, "skipped_existing": skipped, "errors": errors}


# ----------------------------------------------------------------- generate


def _syllabus_text(db: Session, course_id: str) -> str:
    up = db.scalar(
        select(SyllabusUpload).where(SyllabusUpload.course_id == course_id, SyllabusUpload.extracted_text.is_not(None))
        .order_by(SyllabusUpload.created_at.desc()).limit(1)
    )
    return (up.extracted_text if up else None) or ""


def handle_generate(db: Session, job: Job, llm: LLM | None = None, store: VectorStore | None = None) -> dict:
    llm, store = llm or get_llm(), store or get_store()
    course = course_repo.get_with_tree(db, job.course_id)
    if course is None:
        raise UserFacingError("This course no longer exists.")
    levels = [lv for lv in job.params.get("levels") or LEVELS if lv in LEVELS]
    force = bool(job.params.get("force", False))
    only = job.params.get("subtopic_ids")
    text = _syllabus_text(db, course.id)
    targets = [(t, s) for t in course.topics for s in t.subtopics if not only or s.id in only]
    if not targets:
        raise UserFacingError("There are no sub-topics to generate content for.")

    generated, skipped, failed, warnings = 0, 0, [], {}
    for i, (topic, sub) in enumerate(targets, 1):
        set_progress(db, job, f"Writing “{sub.title}”", i - 1, len(targets))
        # Work out what is missing, level by level. Hand-written content counts as present, and a
        # hand-written baseline summary counts as the beginner level.
        have_cards = {c.level for c in sub.flashcards}
        have_summaries = set(sub.summaries or {}) | ({"beginner"} if sub.summary else set())
        card_need = levels if force else [lv for lv in levels if lv not in have_cards]
        summary_need = levels if force else [lv for lv in levels if lv not in have_summaries]
        counts = {lv: sum(1 for q in sub.questions if q.level == lv) for lv in levels}
        need = levels if force else [lv for lv in levels if counts[lv] < MIN_QUESTIONS_PER_LEVEL]
        want_material = force or bool(card_need) or not sub.remediation
        if not want_material and not need and not summary_need:
            skipped += 1  # already generated (or hand-written): never regenerate silently
            continue
        try:
            out = generate_content(llm, store, {
                "course_id": course.id, "syllabus_text": text, "topic": topic.title, "subtopic": sub.title,
                "description": sub.description, "points": sub.key_points or [], "levels": need,
                "flashcard_levels": card_need or levels, "want_material": want_material,
                "summary_levels": summary_need, "verify": get_settings().verify_questions,
                "existing_stems": [] if force else [q.text for q in sub.questions],
            })
            _apply(sub, out, force, set(card_need))
            db.commit()
            generated += 1
            if out["warnings"]:
                warnings[sub.id] = out["warnings"]
        except LLMError as e:
            db.rollback()
            failed.append({"subtopic_id": sub.id, "title": sub.title, "error": str(e)})
    if failed and not generated and not skipped:
        raise UserFacingError(f"Nothing could be generated: {failed[0]['error']}")
    set_progress(db, job, "Done", len(targets), len(targets))
    return {"generated": generated, "skipped": skipped, "failed": failed, "warnings": warnings}


def _apply(sub: Subtopic, out: dict, force: bool, card_levels: set[str]) -> None:
    """Write generated content onto the sub-topic."""
    written = out.get("summaries") or {}
    if written:
        sub.summaries = {**(sub.summaries or {}), **written}  # a new dict, so the change is saved
        if force or not sub.summary:  # keep a hand-written baseline unless asked to regenerate
            sub.summary = sub.summaries[min(sub.summaries, key=LEVELS.index)]
    m = out.get("material")
    if m:
        # Write cards only for levels that were missing (or all, when forced). Other levels' cards,
        # hand-written or from an earlier run, are kept as they are.
        cards = [c for c in m.flashcards if force or c.level in card_levels]
        wrote = {c.level for c in cards}
        keep_cards = [c for c in sub.flashcards if c.level not in wrote]
        start = max((c.position for c in keep_cards), default=0)
        sub.flashcards = keep_cards + [
            Flashcard(id=new_id(), position=start + i, level=c.level, front=c.front.strip(), back=c.back.strip())
            for i, c in enumerate(cards, 1)
        ]
        if force or not sub.remediation:
            sub.remediation = [RemediationItem(id=new_id(), explanation=m.remediation.explanation.strip(),
                                               steps=[s.strip() for s in m.remediation.steps])]
    regenerated = set(out["questions"])  # levels that produced enough verified questions
    # Forced: replace a level only if it regenerated successfully (never leave one empty).
    # Otherwise: keep what exists (hand-written or earlier) and add to it.
    keep = [q for q in sub.questions if not (force and q.level in regenerated)]
    position = max((q.position for q in keep), default=0)
    new = []
    for lvl in LEVELS:
        for q in out["questions"].get(lvl, []):
            position += 1
            new.append(Question(id=new_id(), position=position, level=lvl, type="mcq", text=q.text.strip(),
                                options=[o.strip() for o in q.options], answer_index=q.answer_index,
                                explanation=q.explanation.strip()))
    sub.questions = keep + new


def handle_plan(db: Session, job: Job) -> dict:
    from app.services.planning import handle_plan as run  # imported late: it depends on the learning service

    return run(db, job)


HANDLERS = {"analyze": handle_analyze, "derive": handle_derive, "generate": handle_generate, "plan": handle_plan}

__all__ = ["HANDLERS", "collection_name"]
