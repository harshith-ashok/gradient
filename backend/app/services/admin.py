"""Management dashboard: every student's progress, plus per-student detail."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Enrollment, User
from app.repos import courses as course_repo
from app.services import metrics
from app.services.planner import avg
from app.services.settings import threshold_for

STATUSES = ("on-track", "attention", "completed")
MAX_PAGE_SIZE = 100


class AdminError(Exception):
    def __init__(self, message: str, status_code: int = 404):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _student(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "student_id": u.student_id,
            "program": u.program, "year": u.year}


def overview(db: Session, q: str = "", course_id: str | None = None, status: str | None = None,
             page: int = 1, page_size: int = 20) -> dict:
    """KPIs and course stats cover everyone; the student table is filtered and paginated.

    Everything is loaded in a fixed number of queries (relationships are batch-loaded), so the cost
    does not grow with the number of students beyond the work of summarising each enrolment.
    """
    page, page_size = max(1, page), min(max(1, page_size), MAX_PAGE_SIZE)
    students = list(db.scalars(select(User).where(User.role == "student").order_by(User.name)))
    courses = {c.id: c for c in course_repo.all_with_structure(db)}
    thresholds = {cid: threshold_for(db, c) for cid, c in courses.items()}  # once per course, not per row
    enrollments = db.scalars(
        select(Enrollment).options(
            selectinload(Enrollment.tasks), selectinload(Enrollment.mastery),
            selectinload(Enrollment.attempts), selectinload(Enrollment.day_statuses),
        )
    )
    by_student: dict[str, list[dict]] = {}
    for e in enrollments:
        summary = metrics.enrollment_summary(db, e, courses[e.course_id], thresholds[e.course_id])
        by_student.setdefault(e.user_id, []).append(summary)

    rows: list[dict] = []
    for s in students:
        mine = sorted(by_student.get(s.id, []), key=lambda x: x["code"])
        if not mine:
            rows.append({"student": _student(s), "enrollment": None})
        rows.extend({"student": _student(s), "enrollment": m} for m in mine)

    enrolled = [r for r in rows if r["enrollment"]]
    kpis = {
        "students": len(students),
        "active_learners": len({r["student"]["id"] for r in enrolled}),
        "average_progress": avg([r["enrollment"]["overall"] for r in enrolled]),
        "need_attention": sum(1 for r in enrolled if r["enrollment"]["status"] == "attention"),
    }
    course_stats = []
    for c in courses.values():
        if c.status != "published":
            continue
        es = [r["enrollment"] for r in enrolled if r["enrollment"]["course_id"] == c.id]
        course_stats.append({
            "id": c.id, "code": c.code, "title": c.title, "enrolled": len(es),
            "average": avg([e["overall"] for e in es]), "threshold": thresholds[c.id],
        })

    needle = q.strip().lower()

    def keep(r: dict) -> bool:
        s, e = r["student"], r["enrollment"]
        if needle and needle not in f"{s['name']} {s['email']} {s['student_id'] or ''}".lower():
            return False
        if course_id and (e is None or e["course_id"] != course_id):
            return False
        return not (status and (e is None or e["status"] != status))

    filtered = [r for r in rows if keep(r)]
    start = (page - 1) * page_size
    return {
        "kpis": kpis, "courses": course_stats, "rows": filtered[start:start + page_size],
        "total": len(filtered), "page": page, "page_size": page_size,
    }


def student_detail(db: Session, student_id: str) -> dict:
    u = db.get(User, student_id)
    if u is None or u.role != "student":
        raise AdminError("Student not found.")
    enrs = db.scalars(select(Enrollment).where(Enrollment.user_id == u.id).order_by(Enrollment.created_at))
    out = []
    for e in enrs:
        course = course_repo.get_with_tree(db, e.course_id)
        out.append(metrics.enrollment_detail(db, e, course))
    return {"student": _student(u), "enrollments": out}
