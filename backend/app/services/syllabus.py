"""Faculty-facing syllabus workflow: upload, then derive topics, then generate content."""

import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.ingest import IngestError, detect_kind
from app.core import clock
from app.core.config import get_settings
from app.models import Course, Job, SyllabusUpload, User
from app.models.base import new_id
from app.services import jobs
from app.services.courses import CourseError, _owned

ACCENTS = ["#8e2433", "#2b5565", "#4d6b2f", "#6b4e9b", "#a1642a"]
MAX_TEXT_CHARS = 200_000


def _safe_name(name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name or "syllabus").name)[:120].strip("._")
    return base or "syllabus"


def create_upload(db: Session, user: User, *, code: str, title: str, department: str | None,
                  file_name: str | None, data: bytes | None, text: str | None) -> tuple[Course, SyllabusUpload, Job]:
    code, title = code.strip(), title.strip()
    if not code or not title:
        raise CourseError("Course code and title are required.")
    if len(code) > 24 or len(title) > 200:
        raise CourseError("Course code or title is too long.")
    text = (text or "").strip()
    if not data and not text:
        raise CourseError("Upload a syllabus file or paste its text.")
    if data and text:
        raise CourseError("Provide either a file or pasted text, not both.")
    if text and not 20 <= len(text) <= MAX_TEXT_CHARS:
        raise CourseError("Pasted text must be between 20 and 200,000 characters.")
    s = get_settings()
    if data:
        if len(data) > s.max_upload_mb * 1024 * 1024:
            raise CourseError(f"The file is larger than {s.max_upload_mb} MB.", 413)
        try:
            detect_kind(data, file_name or "")  # reject unsupported or mislabelled files up front
        except IngestError as e:
            raise CourseError(str(e), 415) from e

    course = Course(id=new_id(), code=code, title=title, department=department or user.department,
                    accent=ACCENTS[int(new_id()[:4], 16) % len(ACCENTS)], description="", owner_id=user.id,
                    status="draft", source_file=file_name if data else "pasted text")
    up = SyllabusUpload(id=new_id(), course_id=course.id, file_name=file_name if data else "pasted-text",
                        status="uploaded", uploader_id=user.id, extracted_text=text or None,
                        created_at=clock.now(), updated_at=clock.now())
    db.add_all([course, up])
    db.flush()
    if data:
        rel = f"{up.id}/{_safe_name(file_name or '')}"
        path = Path(s.upload_dir) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        up.file_ref = rel
    job = jobs.enqueue(db, "analyze", user_id=user.id, course_id=course.id, upload_id=up.id)
    return course, up, job


def owned_upload(db: Session, user: User, upload_id: str) -> SyllabusUpload:
    up = db.get(SyllabusUpload, upload_id)
    if up is None:
        raise CourseError("Upload not found.", 404)
    _owned(db, user, up.course_id)  # raises 404/403 for someone else's course
    return up


def latest_job(db: Session, upload_id: str) -> Job | None:
    return db.scalar(select(Job).where(Job.upload_id == upload_id).order_by(Job.created_at.desc()).limit(1))


def request_derive(db: Session, user: User, upload_id: str, topics: list[str], replace: bool) -> Job:
    up = owned_upload(db, user, upload_id)
    if up.status not in ("topics_ready", "derived", "failed") or not up.topics:
        raise CourseError("Topics are not ready yet. Wait for the analysis to finish.", 409)
    known = {t["title"].strip().lower() for t in up.topics}
    unknown = [t for t in topics if t.strip().lower() not in known]
    if unknown:
        raise CourseError(f"Unknown topic: {unknown[0]}")
    return jobs.enqueue(db, "derive", user_id=user.id, course_id=up.course_id, upload_id=up.id,
                        params={"topics": topics, "replace": replace})


def request_generate(db: Session, user: User, course_id: str, subtopic_ids: list[str] | None,
                     levels: list[str] | None, force: bool) -> Job:
    course = _owned(db, user, course_id)
    ids = {s.id for t in course.topics for s in t.subtopics}
    if not ids:
        raise CourseError("This course has no sub-topics yet. Derive them from the syllabus first.", 409)
    if subtopic_ids and (bad := [i for i in subtopic_ids if i not in ids]):
        raise CourseError(f"Unknown sub-topic: {bad[0]}")
    return jobs.enqueue(db, "generate", user_id=user.id, course_id=course.id,
                        params={"subtopic_ids": subtopic_ids, "levels": levels, "force": force})
