"""Idempotent seed: demo users, the three demo courses with content, default settings.

Run with `python -m app.seed.run`. Existing rows (matched by id) are left alone, so it is safe
to run on every start. Seeded student history (enrolments, attempts) arrives with Phase 3.
"""

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.db import session_factory
from app.core.security import hash_password
from app.models import (
    Course,
    Flashcard,
    Question,
    RemediationItem,
    Setting,
    Subtopic,
    Topic,
    User,
)

FIXTURES = Path(__file__).parent / "fixtures"
DEFAULT_PASS_MARK = 70


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


def seed_users(db: Session) -> int:
    n = 0
    for u in _load("users.json"):
        if db.get(User, u["id"]):
            continue
        data = {k: v for k, v in u.items() if k != "password"}
        db.add(User(**data, password_hash=hash_password(u["password"])))
        n += 1
    return n


def _build_subtopic(s: dict, position: int) -> Subtopic:
    sub = Subtopic(
        id=s["id"], position=position, title=s["title"], description=s.get("description", ""),
        key_points=s["points"], summary=s["summary"],
    )
    sub.flashcards = [
        Flashcard(id=f"{s['id']}-f{i}", position=i, front=c["front"], back=c["back"])
        for i, c in enumerate(s["flashcards"], 1)
    ]
    sub.questions = [
        Question(
            id=q["id"], position=i, text=q["text"], options=q["options"],
            answer_index=q["answer"], explanation=q["explanation"],
        )
        for i, q in enumerate(s["questions"], 1)
    ]
    r = s.get("remediation")
    if r:
        sub.remediation = [
            RemediationItem(id=f"{s['id']}-r1", explanation=r["explanation"], steps=r["steps"])
        ]
    return sub


def seed_courses(db: Session) -> int:
    n = 0
    for c in _load("courses.json"):
        if db.get(Course, c["id"]):
            continue
        course = Course(
            id=c["id"], code=c["code"], title=c["title"], department=c.get("department"),
            credits=c.get("credits"), level_label=c.get("level"), accent=c.get("accent"),
            description=c.get("description", ""), owner_id=c["instructorId"], status=c["status"],
            source_file=(c.get("source") or {}).get("fileName"),
        )
        course.topics = [
            Topic(
                id=t["id"], position=ti, title=t["title"],
                subtopics=[_build_subtopic(s, si) for si, s in enumerate(t["subtopics"], 1)],
            )
            for ti, t in enumerate(c["topics"], 1)
        ]
        db.add(course)
        n += 1
    return n


def seed_settings(db: Session) -> None:
    if not db.get(Setting, "pass_mark"):
        db.add(Setting(key="pass_mark", value=DEFAULT_PASS_MARK))


def run(db: Session, history: bool = True) -> dict:
    result = {"users": seed_users(db)}
    db.flush()  # users must exist before courses reference them
    result["courses"] = seed_courses(db)
    seed_settings(db)
    db.commit()
    if history:
        from app.seed.history import seed_history

        result["history"] = seed_history(db)
    return result


if __name__ == "__main__":
    with session_factory()() as session:
        print("seeded:", run(session))
