from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, Setting

DEFAULT_PASS_MARK = 70


def global_pass_mark(db: Session) -> int:
    row = db.get(Setting, "pass_mark")
    return int(row.value) if row else DEFAULT_PASS_MARK


def threshold_for(db: Session, course: Course) -> int:
    """Per-course override if set, otherwise the global pass mark."""
    return course.pass_mark if course.pass_mark is not None else global_pass_mark(db)


MIN_PASS_MARK = 40
MAX_PASS_MARK = 100


class SettingsError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def settings_view(db: Session) -> dict:
    """Global pass mark plus every course with its override and the mark that actually applies."""
    g = global_pass_mark(db)
    courses = db.scalars(select(Course).order_by(Course.code))
    return {
        "global_threshold": g,
        "min": MIN_PASS_MARK,
        "max": MAX_PASS_MARK,
        "courses": [
            {"id": c.id, "code": c.code, "title": c.title, "status": c.status,
             "override": c.pass_mark, "effective": c.pass_mark if c.pass_mark is not None else g}
            for c in courses
        ],
    }


def update_settings(db: Session, global_threshold: int, per_course: dict[str, int | None]) -> dict:
    """Replace the pass mark settings. Courses missing from `per_course` fall back to the global mark.

    The mark is read fresh whenever a quiz is started or graded, so a change applies to every
    quiz from now on (including quizzes already open but not yet submitted).
    """
    def valid(n: object) -> bool:
        return isinstance(n, int) and not isinstance(n, bool) and MIN_PASS_MARK <= n <= MAX_PASS_MARK

    if not valid(global_threshold):
        raise SettingsError(f"Pass mark must be a whole number from {MIN_PASS_MARK} to {MAX_PASS_MARK}.")
    courses = {c.id: c for c in db.scalars(select(Course))}
    for cid, v in per_course.items():
        if cid not in courses:
            raise SettingsError(f"Unknown course: {cid}", 404)
        if v is not None and not valid(v):
            raise SettingsError(f"Course pass mark must be a whole number from {MIN_PASS_MARK} to {MAX_PASS_MARK}.")

    row = db.get(Setting, "pass_mark")
    if row is None:
        db.add(Setting(key="pass_mark", value=global_threshold))
    else:
        row.value = global_threshold
    for cid, c in courses.items():
        c.pass_mark = per_course.get(cid)
    db.commit()
    return settings_view(db)
