"""Read-only aggregates over one enrollment, for the student dashboard and progress pages."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.models import Course, Enrollment, Job
from app.services.planner import FLEX, MIN_FLEX, avg
from app.services.settings import threshold_for


def sub_status(rec, threshold: int) -> str:
    if rec is None:
        return "new"
    if rec.needs_review:
        return "review"
    if rec.last_score is not None and rec.last_score >= threshold:
        return "mastered"
    if rec.studied or rec.attempts > 0:
        return "learning"
    return "new"


def task_out(r) -> dict:
    return {
        "id": r.id, "type": r.type, "topic_id": r.topic_id, "subtopic_id": r.subtopic_id,
        "title": r.title, "minutes": r.minutes, "day": r.day_index, "date": r.scheduled_for,
        "done": r.status == "done", "done_at": r.completed_at, "result": r.result, "note": r.note,
    }


def status_out(d) -> dict:
    return {
        "id": d.id, "day_index": d.day_index, "day": d.day_index + 1, "date": d.date,
        "mastery": d.mastery, "message": d.message, "created_at": d.created_at,
    }


def attempt_out(a) -> dict:
    return {
        "id": a.id, "kind": a.kind, "title": a.title, "score": a.score, "correct": a.correct,
        "total": a.total, "passed": a.passed, "threshold": a.pass_mark, "created_at": a.created_at,
    }


def enrollment_summary(db: Session, enr: Enrollment, course: Course, thr: int | None = None) -> dict:
    """Pass `thr` when summarising many enrolments so the pass mark is not looked up for each one."""
    thr = threshold_for(db, course) if thr is None else thr
    mastery = {m.subtopic_id: m for m in enr.mastery}
    subs = [s for t in course.topics for s in t.subtopics]
    value = lambda s: mastery[s.id].score if s.id in mastery else 0  # noqa: E731
    pending = [t for t in enr.tasks if t.status != "done"]
    today = clock.today()
    remediation = sum(1 for s in subs if s.id in mastery and mastery[s.id].needs_review)
    all_mastered = all(sub_status(mastery.get(s.id), thr) == "mastered" for s in subs)
    return {
        "enrollment_id": enr.id, "course_id": course.id, "code": course.code, "title": course.title,
        "accent": course.accent, "overall": avg([value(s) for s in subs]), "threshold": thr,
        "topics": [
            {"id": t.id, "title": t.title, "mastery": avg([value(s) for s in t.subtopics])}
            for t in course.topics
        ],
        "upcoming": [
            {"id": t.id, "title": t.title, "type": t.type, "date": t.scheduled_for, "minutes": t.minutes}
            for t in pending[:4]
        ],
        "pending_count": len(pending),
        "today_tasks": [task_out(t) for t in enr.tasks if t.scheduled_for == today],
        "plan_done": sum(1 for t in enr.tasks if t.status == "done"),
        "plan_total": len(enr.tasks),
        "remediation_count": remediation,
        "attempts": len(enr.attempts),
        "last_activity": enr.attempts[-1].created_at if enr.attempts else enr.created_at,
        "pretest_score": enr.pretest_score,
        "latest_day_status": status_out(enr.day_statuses[-1]) if enr.day_statuses else None,
        "status": (
            "completed" if all_mastered and not pending else "attention" if remediation else "on-track"
        ),
        "day_number": (today - enr.plan_start_date).days + 1,
        "today": today,
    }


def plan_window(db: Session, enr: Enrollment) -> dict:
    open_ = [t for t in enr.tasks if t.status != "done"]
    today_idx = max(0, (clock.today() - enr.plan_start_date).days)
    days_left = max(1, enr.target_days - today_idx)
    floor_total = sum(MIN_FLEX if t.type in FLEX else t.minutes for t in open_)
    last = max((t.day_index for t in open_), default=None)
    return {
        "target_days": enr.target_days,
        "ends_on": enr.plan_start_date + timedelta(days=enr.target_days - 1),
        "fits": last is None or last < enr.target_days,
        "finish_date": enr.plan_start_date + timedelta(days=last) if last is not None else None,
        "needed_minutes_per_day": -(-floor_total // days_left),
    }


def is_planning(db: Session, enr: Enrollment) -> bool:
    return db.scalar(select(Job.id).where(Job.type == "plan", Job.enrollment_id == enr.id,
                                          Job.status.in_(("queued", "running"))).limit(1)) is not None


def enrollment_detail(db: Session, enr: Enrollment, course: Course, thr: int | None = None) -> dict:
    thr = threshold_for(db, course) if thr is None else thr
    mastery = {m.subtopic_id: m for m in enr.mastery}
    pre = {p.subtopic_id: p.score for p in enr.pretest_results}
    titles = {s.id: s.title for t in course.topics for s in t.subtopics}
    out = enrollment_summary(db, enr, course, thr)

    def sub_row(s):
        rec = mastery.get(s.id)
        return {
            "id": s.id, "title": s.title, "mastery": rec.score if rec else 0,
            "last_score": rec.last_score if rec else None, "attempts": rec.attempts if rec else 0,
            "status": sub_status(rec, thr), "level": rec.level if rec else "beginner",
        }

    out.update({
        "start_date": enr.plan_start_date,
        "minutes_per_day": enr.minutes_per_day,
        "target_days": enr.target_days,
        "plan_window": plan_window(db, enr),
        "planning": is_planning(db, enr),
        "notices": [
            {"id": n.id, "kind": n.kind, "text": n.text, "created_at": n.created_at}
            for n in reversed(enr.notices)
        ],
        "tasks": [task_out(t) for t in enr.tasks],
        "day_statuses": [status_out(d) for d in reversed(enr.day_statuses)],
        "pretest": {
            "taken_at": enr.pretest_completed_at,
            "score": enr.pretest_score,
            "by_subtopic": [
                {"subtopic_id": sid, "title": titles.get(sid, ""), "score": sc} for sid, sc in pre.items()
            ],
        },
        "topic_detail": [
            {
                "id": t.id, "title": t.title,
                "mastery": avg([mastery[s.id].score if s.id in mastery else 0 for s in t.subtopics]),
                "subtopics": [sub_row(s) for s in t.subtopics],
            }
            for t in course.topics
        ],
        "history": [
            {**attempt_out(a), "course_id": course.id} for a in reversed(enr.attempts)
        ],
    })
    return out
