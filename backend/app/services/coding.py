"""Coding challenges: authoring (faculty) and solving (students)."""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core import cache
from app.core.config import get_settings
from app.models import CodeSubmission, CodingProblem, Course, Subtopic, Topic, User
from app.models.base import new_id
from app.schemas.coding import ProblemIn
from app.services.courses import CourseError, _owned


def _subtopic_course(db: Session, subtopic_id: str) -> tuple[Subtopic, Topic, Course]:
    sub = db.get(Subtopic, subtopic_id)
    if sub is None:
        raise CourseError("Sub-topic not found.", 404)
    topic = db.get(Topic, sub.topic_id)
    return sub, topic, db.get(Course, topic.course_id)


def _problem(db: Session, problem_id: str) -> CodingProblem:
    p = db.get(CodingProblem, problem_id)
    if p is None:
        raise CourseError("Problem not found.", 404)
    return p


# ------------------------------------------------------------------ authoring (faculty)


def _out(p: CodingProblem) -> dict:
    return {"id": p.id, "subtopic_id": p.subtopic_id, "position": p.position, "title": p.title,
            "statement": p.statement, "level": p.level, "languages": p.languages, "starter": p.starter,
            "time_limit_ms": p.time_limit_ms, "memory_mb": p.memory_mb, "tests": p.tests}


def _check(body: ProblemIn) -> None:
    if not any(t.sample for t in body.tests):
        raise CourseError("Mark at least one test as a sample so students see an example.")
    if not body.statement.strip():
        raise CourseError("Write the problem statement.")


def _owned_problem(db: Session, user: User, problem_id: str) -> tuple[CodingProblem, Course]:
    p = _problem(db, problem_id)
    course = _subtopic_course(db, p.subtopic_id)[2]
    _owned(db, user, course.id)
    return p, course


def staff_list(db: Session, user: User, subtopic_id: str) -> list[dict]:
    _owned(db, user, _subtopic_course(db, subtopic_id)[2].id)
    rows = db.scalars(select(CodingProblem).where(CodingProblem.subtopic_id == subtopic_id)
                      .order_by(CodingProblem.position))
    return [_out(p) for p in rows]


def staff_create(db: Session, user: User, subtopic_id: str, body: ProblemIn) -> dict:
    _owned(db, user, _subtopic_course(db, subtopic_id)[2].id)
    _check(body)
    last = db.scalar(select(func.max(CodingProblem.position)).where(CodingProblem.subtopic_id == subtopic_id)) or 0
    p = CodingProblem(id=new_id(), subtopic_id=subtopic_id, position=last + 1)
    _apply(p, body)
    db.add(p)
    db.commit()
    return _out(p)


def _apply(p: CodingProblem, body: ProblemIn) -> None:
    p.title, p.statement, p.level = body.title.strip(), body.statement, body.level
    p.languages = list(body.languages)
    p.starter = {k: v for k, v in body.starter.items() if k in body.languages}
    p.time_limit_ms, p.memory_mb = body.time_limit_ms, body.memory_mb
    p.tests = [t.model_dump() for t in body.tests]


def staff_update(db: Session, user: User, problem_id: str, body: ProblemIn) -> dict:
    p, _ = _owned_problem(db, user, problem_id)
    _check(body)
    _apply(p, body)
    db.commit()
    return _out(p)


def staff_delete(db: Session, user: User, problem_id: str) -> None:
    p, _ = _owned_problem(db, user, problem_id)
    db.execute(delete(CodeSubmission).where(CodeSubmission.problem_id == p.id))
    db.delete(p)
    db.commit()


# ------------------------------------------------------------------ submissions


def _enqueue(db: Session, user: User, p: CodingProblem, language: str, code: str, mode: str) -> CodeSubmission:
    s = get_settings()
    if language not in p.languages:
        raise CourseError("That language is not allowed for this problem.")
    if len(code.encode()) > s.max_code_bytes:
        raise CourseError(f"Your code is longer than {s.max_code_bytes // 1000} KB.", 413)
    busy = db.scalar(select(func.count()).where(CodeSubmission.user_id == user.id,
                                                CodeSubmission.state.in_(("queued", "running"))))
    if busy:
        raise CourseError("Your previous run is still going. Wait for it to finish.", 429)
    try:  # a per-minute cap; if Redis is down we skip it rather than block everyone
        key = f"submit:{user.id}"
        n = cache._client().incr(key)
        if n == 1:
            cache._client().expire(key, 60)
        if n > s.submissions_per_minute:
            raise CourseError("You are running code too quickly. Wait a minute.", 429)
    except CourseError:
        raise
    except Exception:  # noqa: BLE001
        pass
    sub = CodeSubmission(id=new_id(), problem_id=p.id, user_id=user.id, language=language, mode=mode, code=code,
                         state="queued", passed=0, total=0, results=[])
    db.add(sub)
    db.commit()
    return sub


def _submission_out(db: Session, s: CodeSubmission) -> dict:
    ahead = None
    if s.state == "queued":
        ahead = db.scalar(select(func.count()).where(CodeSubmission.state == "queued",
                                                     CodeSubmission.created_at < s.created_at)) or 0
    return {"id": s.id, "problem_id": s.problem_id, "language": s.language, "mode": s.mode, "state": s.state,
            "verdict": s.verdict, "passed": s.passed, "total": s.total, "runtime_ms": s.runtime_ms,
            "compile_output": s.compile_output, "message": s.message, "results": s.results or [],
            "code": s.code, "created_at": s.created_at, "queue_position": ahead}


def staff_run(db: Session, user: User, problem_id: str, language: str, code: str) -> dict:
    p, _ = _owned_problem(db, user, problem_id)
    return {"id": _enqueue(db, user, p, language, code, "check").id}


def staff_submission(db: Session, user: User, submission_id: str) -> dict:
    s = db.get(CodeSubmission, submission_id)
    if s is None:
        raise CourseError("Submission not found.", 404)
    _owned_problem(db, user, s.problem_id)
    return _submission_out(db, s)


# ------------------------------------------------------------------ students


def _published(db: Session, problem: CodingProblem) -> tuple[Subtopic, Course]:
    sub, _, course = _subtopic_course(db, problem.subtopic_id)
    if course.status != "published":
        raise CourseError("Problem not found.", 404)
    return sub, course


def student_list(db: Session, user: User, subtopic_id: str) -> list[dict]:
    sub, _, course = _subtopic_course(db, subtopic_id)
    if course.status != "published":
        raise CourseError("Sub-topic not found.", 404)
    problems = list(db.scalars(select(CodingProblem).where(CodingProblem.subtopic_id == sub.id)
                               .order_by(CodingProblem.position)))
    if not problems:
        return []
    ids = [p.id for p in problems]
    attempts = dict(db.execute(select(CodeSubmission.problem_id, func.count())
                               .where(CodeSubmission.user_id == user.id, CodeSubmission.problem_id.in_(ids),
                                      CodeSubmission.mode == "submit").group_by(CodeSubmission.problem_id)).all())
    solved = set(db.scalars(select(CodeSubmission.problem_id)
                            .where(CodeSubmission.user_id == user.id, CodeSubmission.problem_id.in_(ids),
                                   CodeSubmission.mode == "submit", CodeSubmission.verdict == "accepted")))
    return [{"id": p.id, "title": p.title, "level": p.level, "languages": p.languages,
             "solved": p.id in solved, "attempts": attempts.get(p.id, 0)} for p in problems]


def student_detail(db: Session, user: User, problem_id: str) -> dict:
    p = _problem(db, problem_id)
    sub, course = _published(db, p)
    solved = bool(db.scalar(select(func.count()).where(
        CodeSubmission.user_id == user.id, CodeSubmission.problem_id == p.id,
        CodeSubmission.mode == "submit", CodeSubmission.verdict == "accepted")))
    samples = [{"input": t["input"], "expected": t["expected"]} for t in p.tests if t.get("sample")]
    return {"id": p.id, "title": p.title, "statement": p.statement, "level": p.level, "languages": p.languages,
            "starter": p.starter, "time_limit_ms": p.time_limit_ms, "memory_mb": p.memory_mb, "samples": samples,
            "hidden_tests": len(p.tests) - len(samples), "solved": solved, "subtopic_id": sub.id,
            "subtopic_title": sub.title, "course_id": course.id, "course_code": course.code,
            "course_title": course.title}


def student_submit(db: Session, user: User, problem_id: str, language: str, code: str, mode: str) -> dict:
    p = _problem(db, problem_id)
    _published(db, p)
    return {"id": _enqueue(db, user, p, language, code, mode).id}


def student_submission(db: Session, user: User, submission_id: str) -> dict:
    s = db.get(CodeSubmission, submission_id)
    if s is None or s.user_id != user.id:
        raise CourseError("Submission not found.", 404)
    return _submission_out(db, s)


def student_history(db: Session, user: User, problem_id: str) -> list[CodeSubmission]:
    _published(db, _problem(db, problem_id))
    return list(db.scalars(select(CodeSubmission).where(CodeSubmission.user_id == user.id,
                                                        CodeSubmission.problem_id == problem_id)
                           .order_by(CodeSubmission.created_at.desc()).limit(10)))
