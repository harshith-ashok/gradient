"""Course reads for students and course management for staff (ported from prototype courses.js)."""

from sqlalchemy.orm import Session

from app.core import cache
from app.models import Course, Flashcard, Question, RemediationItem, Subtopic, Topic, User
from app.models.base import new_id
from app.repos import courses as repo
from app.schemas.course import CourseSave
from app.services.settings import threshold_for

CACHE_TTL = 300


class CourseError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _counts(c: Course) -> tuple[int, int]:
    return len(c.topics), sum(len(t.subtopics) for t in c.topics)


# ---------------------------------------------------------------- students


def _card(db: Session, c: Course, instructor: str) -> dict:
    topics, subtopics = _counts(c)
    return {
        "id": c.id, "code": c.code, "title": c.title, "department": c.department,
        "credits": c.credits, "level": c.level_label, "accent": c.accent,
        "description": c.description, "instructor": instructor,
        "threshold": threshold_for(db, c), "topic_count": topics, "subtopic_count": subtopics,
    }


def catalog(db: Session) -> list[dict]:
    courses = repo.list_published(db)
    names = repo.user_names(db, {c.owner_id for c in courses})
    return [_card(db, c, names.get(c.owner_id, "Faculty")) for c in courses]


def _structure_payload(db: Session, c: Course) -> dict:
    """Threshold is added after caching, so a pass mark change never serves a stale value."""
    names = repo.user_names(db, {c.owner_id})
    return {
        "id": c.id, "code": c.code, "title": c.title, "department": c.department,
        "credits": c.credits, "level": c.level_label, "accent": c.accent,
        "description": c.description, "instructor": names.get(c.owner_id, "Faculty"),
        "topic_count": len(c.topics),
        "subtopic_count": sum(len(t.subtopics) for t in c.topics),
        "topics": [
            {
                "id": t.id, "title": t.title,
                "subtopics": [
                    {"id": s.id, "title": s.title, "description": s.description}
                    for s in t.subtopics
                ],
            }
            for t in c.topics
        ],
    }


def course_structure(db: Session, course_id: str) -> dict:
    def load() -> dict:
        c = repo.get_with_tree(db, course_id)
        if c is None or c.status != "published":
            raise CourseError("Course not found.", 404)
        return _structure_payload(db, c)

    # Only successful loads are cached; the 404 raised above is never stored.
    data = cache.cached_json(cache.course_key(course_id), CACHE_TTL, load)
    course = db.get(Course, course_id)
    if course is None or course.status != "published":  # cached entry outlived an unpublish
        raise CourseError("Course not found.", 404)
    return {**data, "threshold": threshold_for(db, course)}


def subtopic_view(db: Session, course_id: str, subtopic_id: str) -> dict:
    c = repo.get_with_tree(db, course_id)
    if c is None or c.status != "published":
        raise CourseError("Course not found.", 404)
    flat = [(t, s) for t in c.topics for s in t.subtopics]
    idx = next((i for i, (_, s) in enumerate(flat) if s.id == subtopic_id), None)
    if idx is None:
        raise CourseError("Sub-topic not found.", 404)
    topic, sub = flat[idx]
    nav = lambda i: {"id": flat[i][1].id, "title": flat[i][1].title} if 0 <= i < len(flat) else None  # noqa: E731
    rem = sub.remediation[0] if sub.remediation else None
    return {
        "course": {"id": c.id, "title": c.title},
        "course_code": c.code,
        "topic": {"id": topic.id, "title": topic.title},
        "subtopic": {
            "id": sub.id, "title": sub.title, "description": sub.description,
            "points": sub.key_points, "summary": sub.summary,
            "flashcards": [{"front": f.front, "back": f.back} for f in sub.flashcards],
            "remediation": {"explanation": rem.explanation, "steps": rem.steps} if rem else None,
        },
        "threshold": threshold_for(db, c),
        "prev": nav(idx - 1),
        "next": nav(idx + 1),
    }


# ------------------------------------------------------------------- staff


def _owned(db: Session, user: User, course_id: str) -> Course:
    c = repo.get_with_tree(db, course_id)
    if c is None:
        raise CourseError("Course not found.", 404)
    if user.role == "faculty" and c.owner_id != user.id:
        raise CourseError("You can only edit your own courses.", 403)
    return c


def list_for_staff(db: Session, user: User) -> list[dict]:
    courses = repo.list_for_staff(db, user)
    enrolled = repo.enrolled_counts(db, [c.id for c in courses])
    out = []
    for c in courses:
        topics, subtopics = _counts(c)
        out.append({
            "id": c.id, "code": c.code, "title": c.title, "department": c.department,
            "status": c.status, "accent": c.accent, "source_file": c.source_file,
            "topic_count": topics, "subtopic_count": subtopics,
            "enrolled": enrolled.get(c.id, 0), "threshold": threshold_for(db, c),
        })
    return out


def _full(c: Course) -> dict:
    return {
        "id": c.id, "code": c.code, "title": c.title, "department": c.department,
        "credits": c.credits, "level": c.level_label, "accent": c.accent,
        "description": c.description, "status": c.status, "source_file": c.source_file,
        "owner_id": c.owner_id,
        "topics": [
            {
                "id": t.id, "title": t.title, "summary": t.summary,
                "subtopics": [
                    {
                        "id": s.id, "title": s.title, "description": s.description,
                        "points": s.key_points, "summary": s.summary,
                        "flashcards": [{"front": f.front, "back": f.back} for f in s.flashcards],
                        "questions": [
                            {"id": q.id, "text": q.text, "options": q.options,
                             "answer_index": q.answer_index, "explanation": q.explanation}
                            for q in s.questions
                        ],
                        "remediation": (
                            {"explanation": s.remediation[0].explanation,
                             "steps": s.remediation[0].steps}
                            if s.remediation else None
                        ),
                    }
                    for s in t.subtopics
                ],
            }
            for t in c.topics
        ],
    }


def get_for_staff(db: Session, user: User, course_id: str) -> dict:
    return _full(_owned(db, user, course_id))


def save_course(db: Session, user: User, course_id: str, body: CourseSave) -> dict:
    c = _owned(db, user, course_id)
    if not body.title.strip() or not body.code.strip():
        raise CourseError("Course code and title are required.")
    for t in body.topics:
        if not t.title.strip():
            raise CourseError("Every topic needs a title.")
        for s in t.subtopics:
            if not s.title.strip():
                raise CourseError("Every sub-topic needs a title.")
            for q in s.questions:
                if not 0 <= q.answer_index < len(q.options):
                    raise CourseError(f"A question in “{s.title}” has an invalid correct answer.")

    c.code, c.title = body.code.strip(), body.title.strip()
    c.department, c.credits, c.level_label = body.department, body.credits, body.level
    c.accent, c.description = body.accent, body.description

    existing_topics = {t.id: t for t in c.topics}
    new_topics: list[Topic] = []
    for ti, t in enumerate(body.topics, 1):
        topic = existing_topics.get(t.id or "") or Topic(id=new_id())
        topic.position, topic.title, topic.summary = ti, t.title.strip(), t.summary
        existing_subs = {s.id: s for s in topic.subtopics} if topic.subtopics else {}
        subs: list[Subtopic] = []
        for si, s in enumerate(t.subtopics, 1):
            sub = existing_subs.get(s.id or "") or Subtopic(id=new_id())
            sub.position, sub.title, sub.description = si, s.title.strip(), s.description
            sub.key_points = [p.strip() for p in s.points if p.strip()]
            sub.summary = s.summary
            # Child content is replaced wholesale; question ids are kept so history can refer to them.
            sub.flashcards = [
                Flashcard(position=i, front=f.front, back=f.back) for i, f in enumerate(s.flashcards, 1)
            ]
            old_q = {q.id: q for q in sub.questions}
            questions: list[Question] = []
            for i, q in enumerate(s.questions, 1):
                row = old_q.get(q.id or "") or Question(id=new_id())
                row.position, row.text, row.options = i, q.text, q.options
                row.answer_index, row.explanation = q.answer_index, q.explanation
                questions.append(row)
            sub.questions = questions
            sub.remediation = (
                [RemediationItem(explanation=s.remediation.explanation, steps=s.remediation.steps)]
                if s.remediation else []
            )
            subs.append(sub)
        topic.subtopics = subs
        new_topics.append(topic)
    c.topics = new_topics

    db.commit()
    cache.invalidate(cache.course_key(c.id))
    return _full(repo.get_with_tree(db, c.id))


def set_status(db: Session, user: User, course_id: str, status: str) -> dict:
    c = _owned(db, user, course_id)
    if status == "published":
        if not c.topics:
            raise CourseError("Add at least one topic before publishing.")
        for t in c.topics:
            if not t.subtopics:
                raise CourseError(f"Topic “{t.title}” has no sub-topics.")
            for s in t.subtopics:
                if not s.questions:
                    raise CourseError(
                        f"Sub-topic “{s.title}” has no quiz questions yet. "
                        "Add key points so questions can be generated."
                    )
    c.status = status
    db.commit()
    cache.invalidate(cache.course_key(c.id))
    return {"id": c.id, "status": c.status}
