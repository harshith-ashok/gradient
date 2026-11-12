"""Student learning engine: enrolment, pre-test, personalised plan, quizzes, and the adaptive rules
that react to a low score. Ported from the prototype's learning.js; the rules are deliberately
plain code (no LLM) so they stay deterministic and testable.
"""

import logging
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import get_settings
from app.models import (
    Course,
    DayStatus,
    Enrollment,
    Mastery,
    PlanNotice,
    PlanTask,
    PretestResult,
    QuizAttempt,
    QuizSession,
    Subtopic,
    Topic,
    User,
)
from app.models.base import LEVELS, new_id
from app.repos import courses as course_repo
from app.services import courses as course_svc
from app.services import jobs, metrics
from app.services.planner import (
    MINUTES,
    QUIZ_LIKE,
    Fit,
    SubInfo,
    Task,
    TopicInfo,
    avg,
    build_tasks,
    fit_window,
    insert_later,
    js_round,
    make_task,
    move_topic_quiz_last,
)
from app.services.settings import threshold_for

DEFAULT_MINUTES = 60
MINUTES_OPTIONS = (30, 45, 60, 90, 120)
DEFAULT_DAYS = 21
DAYS_OPTIONS = (7, 14, 21, 30, 45, 60, 90)
log = logging.getLogger(__name__)
SESSION_TTL = timedelta(hours=2)
rng = random.Random()  # tests and the seed can reseed this for repeatable quizzes


class LearningError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ----------------------------------------------------------------- helpers


def _aware(dt: datetime) -> datetime:
    """SQLite hands back naive datetimes; treat them as UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def next_level(level: str) -> str:
    return LEVELS[min(LEVELS.index(level) + 1, len(LEVELS) - 1)]


def _course(db: Session, course_id: str) -> Course:
    c = course_repo.get_with_tree(db, course_id)
    if c is None or c.status != "published":
        raise LearningError("Course not found.", 404)
    return c


def all_subtopics(course: Course) -> list[tuple[Topic, Subtopic]]:
    return [(t, s) for t in course.topics for s in t.subtopics]


def get_enrollment(db: Session, user: User, course_id: str) -> Enrollment | None:
    return db.scalar(
        select(Enrollment).where(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
    )


def _must_enrollment(db: Session, user: User, course: Course) -> Enrollment:
    enr = get_enrollment(db, user, course.id)
    if enr is None:
        raise LearningError("You are not enrolled in this course yet.", 404)
    refresh(db, enr, course)
    return enr


def _mastery_map(enr: Enrollment) -> dict[str, Mastery]:
    return {m.subtopic_id: m for m in enr.mastery}


def _new_mastery(enr: Enrollment, sid: str, score: float = 0, level: str = "beginner") -> Mastery:
    m = Mastery(id=new_id(), enrollment_id=enr.id, subtopic_id=sid, score=score, level=level,
                attempts=0, studied=False, needs_review=False)
    enr.mastery.append(m)
    return m


def _to_tasks(enr: Enrollment) -> list[Task]:
    return [
        Task(id=r.id, type=r.type, topic_id=r.topic_id, subtopic_id=r.subtopic_id, title=r.title,
             minutes=r.minutes, day=r.day_index, scheduled_for=r.scheduled_for,
             done=r.status == "done", done_at=r.completed_at, result=r.result, note=r.note)
        for r in enr.tasks
    ]


def _save_tasks(enr: Enrollment, tasks: list[Task]) -> None:
    existing = {r.id: r for r in enr.tasks}
    rows = []
    for pos, t in enumerate(tasks):
        r = existing.get(t.id) or PlanTask(id=t.id, enrollment_id=enr.id)
        r.type, r.title, r.minutes = t.type, t.title, t.minutes
        r.topic_id, r.subtopic_id = t.topic_id, t.subtopic_id
        r.day_index = t.day or 0
        r.scheduled_for = t.scheduled_for or clock.today()
        r.position = pos
        r.status = "done" if t.done else "todo"
        r.completed_at, r.result, r.note = t.done_at, t.result, t.note
        rows.append(r)
    enr.tasks = rows  # rows that were dropped are deleted (delete-orphan)


def _add_notice(enr: Enrollment, kind: str, text: str) -> None:
    enr.notices.append(PlanNotice(id=new_id(), enrollment_id=enr.id, kind=kind, text=text,
                                  created_at=clock.now()))


def schedule(enr: Enrollment, tasks: list[Task]) -> Fit:
    """Lay the unfinished tasks out so the whole course ends inside the student's time frame."""
    fit = fit_window(tasks, enr.plan_start_date, clock.today(), enr.minutes_per_day, enr.target_days)
    if not fit.fits:
        text = (f"At {enr.minutes_per_day} minutes a day this plan runs {fit.last_day + 1 - enr.target_days} "
                f"{'day' if fit.last_day + 1 - enr.target_days == 1 else 'days'} past your {enr.target_days}-day "
                f"time frame, even with the study sessions shortened. About {fit.needed_minutes_per_day} minutes "
                "a day, or a longer time frame, would cover everything.")
        if not enr.notices or enr.notices[-1].text != text:
            _add_notice(enr, "info", text)
    return fit


def request_replan(db: Session, enr: Enrollment, user_id: str, reason: str) -> None:
    """Ask the worker to have the AI planner re-shape what is left. The plan already works without
    it (the rules above are enough), so this never blocks the student or fails the request."""
    if not get_settings().ai_planning:
        return
    try:
        jobs.enqueue(db, "plan", user_id=user_id, course_id=enr.course_id, enrollment_id=enr.id,
                     params={"reason": reason}, dedupe_on=("queued",))
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("could not queue plan job")


def _finish(t: Task, result: str) -> None:
    t.done, t.done_at, t.result = True, clock.now(), result


def _topic_infos(course: Course) -> list[TopicInfo]:
    return [
        TopicInfo(t.id, t.title, [SubInfo(s.id, s.title) for s in t.subtopics]) for t in course.topics
    ]


def refresh(db: Session, enr: Enrollment, course: Course) -> None:
    """Keep an enrolment consistent with the course and the calendar.

    Unfinished tasks from earlier days roll forward to today and the rest of the plan is repacked.
    """
    sub_ids = {s.id for _, s in all_subtopics(course)}
    topic_ids = {t.id for t in course.topics}
    tasks = _to_tasks(enr)
    kept = [
        t for t in tasks
        if t.done or (t.topic_id in topic_ids and (t.subtopic_id is None or t.subtopic_id in sub_ids))
    ]
    removed = len(tasks) - len(kept)
    have = _mastery_map(enr)
    for sid in sub_ids - have.keys():
        _new_mastery(enr, sid)
    today = clock.today()
    today_idx = max(0, (today - enr.plan_start_date).days)
    overdue = sum(1 for t in kept if not t.done and (t.day or 0) < today_idx)
    if overdue or removed:
        schedule(enr, kept)
        _save_tasks(enr, kept)
        if overdue:
            n = "task" if overdue == 1 else "tasks"
            _add_notice(enr, "recalc", f"{overdue} unfinished {n} from earlier days moved forward "
                                       "and the rest of the plan was recalculated.")
        if removed:
            _add_notice(enr, "recalc", "The course outline changed, so your plan was updated.")
    db.commit()


def _check_days(enr: Enrollment, course: Course, days: set[int]) -> DayStatus | None:
    """When every task of a day is done, record "Day N completed – X% mastery"."""
    mastery = _mastery_map(enr)
    created: list[DayStatus] = []
    for d in sorted(days):
        todays = [t for t in enr.tasks if t.day_index == d]
        if not todays or any(t.status != "done" for t in todays):
            continue
        if any(s.day_index == d for s in enr.day_statuses):
            continue
        sub_ids: set[str] = set()
        for t in todays:
            if t.subtopic_id:
                sub_ids.add(t.subtopic_id)
            else:
                topic = next((x for x in course.topics if x.id == t.topic_id), None)
                if topic:
                    sub_ids.update(s.id for s in topic.subtopics)
        m = avg([mastery[i].score if i in mastery else 0 for i in sub_ids])
        status = DayStatus(
            id=new_id(), enrollment_id=enr.id, day_index=d, date=todays[0].scheduled_for, mastery=m,
            message=f"Day {d + 1} completed – {m}% mastery", created_at=clock.now(),
        )
        enr.day_statuses.append(status)
        created.append(status)
    return created[-1] if created else None


# ----------------------------------------------------------------- quizzes


def pick_questions(sub: Subtopic, n: int, level: str) -> list[dict]:
    """Up to n questions, preferring the student's level, then nearest levels, random within."""
    target = LEVELS.index(level)
    pool = sorted(sub.questions, key=lambda q: (abs(LEVELS.index(q.level) - target), rng.random()))
    out = []
    for q in pool[:n]:
        opts = [(text, i == q.answer_index) for i, text in enumerate(q.options)]
        rng.shuffle(opts)
        out.append({
            "id": q.id, "subtopic_id": sub.id, "text": q.text,
            "options": [t for t, _ in opts], "answer": next(i for i, (_, ok) in enumerate(opts) if ok),
            "explanation": q.explanation,
        })
    return out


def start_quiz(db: Session, user: User, course_id: str, kind: str, topic_id: str | None = None,
               subtopic_id: str | None = None) -> dict:
    course = _course(db, course_id)
    enr = get_enrollment(db, user, course_id)
    levels = {m.subtopic_id: m.level for m in enr.mastery} if enr else {}
    questions: list[dict] = []
    if kind == "pretest":
        if enr:
            raise LearningError("You have already taken the pre-test for this course.")
        for _, s in all_subtopics(course):
            questions += pick_questions(s, 2, "beginner")
        title, scope = f"Pre-test: {course.title}", "Diagnostic across every sub-topic"
    else:
        if not enr:
            raise LearningError("Enrol in this course first.", 404)
        if kind == "topic":
            topic = next((t for t in course.topics if t.id == topic_id), None)
            if not topic:
                raise LearningError("Topic not found.", 404)
            for s in topic.subtopics:
                questions += pick_questions(s, 2, levels.get(s.id, "beginner"))
            title, scope = f"Topic quiz: {topic.title}", f"{len(topic.subtopics)} sub-topics"
        else:
            hit = next(((t, s) for t, s in all_subtopics(course) if s.id == subtopic_id), None)
            if not hit:
                raise LearningError("Sub-topic not found.", 404)
            questions = pick_questions(hit[1], 4, levels.get(hit[1].id, "beginner"))
            label = "Practice quiz" if kind == "practice" else "Quiz"
            title, scope = f"{label}: {hit[1].title}", hit[0].title
    if not questions:
        raise LearningError("No questions are available for this selection yet.")

    # Drop this user's expired sessions, then open a new one.
    cutoff = clock.now() - SESSION_TTL
    db.execute(delete(QuizSession).where(QuizSession.user_id == user.id, QuizSession.created_at < cutoff))
    sess = QuizSession(id=new_id(), user_id=user.id, course_id=course_id, kind=kind, topic_id=topic_id,
                       subtopic_id=subtopic_id, title=title, scope=scope, questions=questions,
                       created_at=clock.now())
    db.add(sess)
    db.commit()
    return {
        "quiz_id": sess.id, "kind": kind, "course_id": course_id, "title": title, "scope": scope,
        "threshold": None if kind == "pretest" else threshold_for(db, course),
        "questions": [{"id": q["id"], "text": q["text"], "options": q["options"]} for q in questions],
    }


def answer_key(db: Session, quiz_id: str) -> dict[str, int]:
    """Reveal the key of an open quiz. Only for the seed script and tests, never an endpoint."""
    sess = db.get(QuizSession, quiz_id)
    return {q["id"]: q["answer"] for q in sess.questions}


def submit_quiz(db: Session, user: User, quiz_id: str, answers: dict[str, int]) -> dict:
    sess = db.get(QuizSession, quiz_id)
    expired = sess is not None and clock.now() - _aware(sess.created_at) > SESSION_TTL
    if sess is None or sess.user_id != user.id or expired:
        if sess is not None and sess.user_id == user.id:
            db.delete(sess)
            db.commit()
        raise LearningError("This quiz session has expired. Please start it again.", 410)
    questions = sess.questions
    kind, course_id, topic_id, subtopic_id, title = (
        sess.kind, sess.course_id, sess.topic_id, sess.subtopic_id, sess.title,
    )
    db.delete(sess)

    course = _course(db, course_id)
    sub_title = {s.id: s.title for _, s in all_subtopics(course)}
    graded = []
    for q in questions:
        chosen = answers.get(q["id"])
        chosen = chosen if isinstance(chosen, int) and not isinstance(chosen, bool) else None
        graded.append({**q, "chosen": chosen, "correct": chosen == q["answer"]})
    per: dict[str, dict] = {}
    for g in graded:
        p = per.setdefault(g["subtopic_id"], {"correct": 0, "total": 0})
        p["total"] += 1
        p["correct"] += g["correct"]
    for p in per.values():
        p["score"] = js_round(100 * p["correct"] / p["total"])
    correct = sum(1 for g in graded if g["correct"])
    score = js_round(100 * correct / len(graded))
    review = [
        {"id": g["id"], "text": g["text"], "options": g["options"], "chosen": g["chosen"],
         "answer": g["answer"], "correct": g["correct"], "explanation": g["explanation"],
         "subtopic_title": sub_title.get(g["subtopic_id"], "")}
        for g in graded
    ]
    ctx = {"user": user, "course": course, "kind": kind, "topic_id": topic_id,
           "subtopic_id": subtopic_id, "title": title, "per": per, "score": score,
           "correct": correct, "total": len(graded), "review": review, "graded": graded,
           "sub_title": sub_title}
    return _finish_pretest(db, ctx) if kind == "pretest" else _finish_quiz(db, ctx)


def _attempt(enr: Enrollment, ctx: dict, passed: bool | None, thr: int | None, breakdown: list) -> None:
    enr.attempts.append(QuizAttempt(
        id=new_id(), user_id=ctx["user"].id, enrollment_id=enr.id, kind=ctx["kind"], title=ctx["title"],
        topic_id=ctx["topic_id"], subtopic_id=ctx["subtopic_id"], score=ctx["score"],
        correct=ctx["correct"], total=ctx["total"], pass_mark=thr, passed=passed, breakdown=breakdown,
        answers=[{"question_id": g["id"], "subtopic_id": g["subtopic_id"], "chosen": g["chosen"],
                  "answer": g["answer"], "correct": g["correct"]} for g in ctx["graded"]],
        created_at=clock.now(),
    ))


def _finish_pretest(db: Session, ctx: dict) -> dict:
    user, course, per = ctx["user"], ctx["course"], ctx["per"]
    thr = threshold_for(db, course)
    today = clock.today()
    enr = Enrollment(
        id=new_id(), user_id=user.id, course_id=course.id, minutes_per_day=DEFAULT_MINUTES,
        target_days=DEFAULT_DAYS,
        plan_start_date=today, pretest_score=ctx["score"], pretest_completed_at=clock.now(),
        created_at=clock.now(), updated_at=clock.now(),
    )
    db.add(enr)
    after: dict[str, float] = {}
    for _, s in all_subtopics(course):
        p = per.get(s.id, {"score": 0})
        # Mastery starts at half the pre-test score. Students who already know a sub-topic
        # start one level up.
        level = "intermediate" if p["score"] >= thr else "beginner"
        after[s.id] = js_round(p["score"] * 0.5)
        _new_mastery(enr, s.id, after[s.id], level)
        enr.pretest_results.append(
            PretestResult(id=new_id(), enrollment_id=enr.id, subtopic_id=s.id, score=p["score"])
        )
    tasks = build_tasks(_topic_infos(course), {sid: p["score"] for sid, p in per.items()}, thr)
    schedule(enr, tasks)
    _save_tasks(enr, tasks)
    known = sum(1 for p in per.values() if p["score"] >= thr)
    need = len(per) - known
    _add_notice(enr, "info",
                f"Plan created from your pre-test: {need} {'sub-topic needs' if need == 1 else 'sub-topics need'}"
                f" full study and {known} {'needs' if known == 1 else 'need'} only a quick confirmation quiz.")
    breakdown = [{"subtopic_id": sid, "score": p["score"], "correct": p["correct"], "total": p["total"]}
                 for sid, p in per.items()]
    _attempt(enr, ctx, None, None, breakdown)
    db.commit()
    request_replan(db, enr, user.id, "The student just finished the pre-test; build the first plan.")
    return {
        "kind": "pretest", "course_id": course.id, "title": ctx["title"], "score": ctx["score"],
        "correct": ctx["correct"], "total": ctx["total"], "passed": None, "threshold": thr,
        "review": ctx["review"],
        "by_subtopic": [
            {"subtopic_id": sid, "title": ctx["sub_title"].get(sid, ""), "score": p["score"],
             "correct": p["correct"], "total": p["total"], "before": None, "after": after[sid],
             "level": _mastery_map(enr)[sid].level, "promoted": False}
            for sid, p in per.items()
        ],
        "actions": None, "day_status": None, "next_task": None,
        "plan": {"days": len({t.day for t in tasks}), "tasks": len(tasks), "minutes_per_day": DEFAULT_MINUTES},
    }


def _finish_quiz(db: Session, ctx: dict) -> dict:
    user, course, per, score = ctx["user"], ctx["course"], ctx["per"], ctx["score"]
    kind, topic_id, subtopic_id = ctx["kind"], ctx["topic_id"], ctx["subtopic_id"]
    enr = _must_enrollment(db, user, course)
    thr = threshold_for(db, course)
    passed = score >= thr
    tasks = _to_tasks(enr)
    touched: set[int] = set()
    sub_title = ctx["sub_title"]

    def done(t: Task, result: str) -> None:
        _finish(t, result)
        touched.add(t.day or 0)

    def topic_of(sid: str) -> Topic:
        return next(t for t in course.topics if any(s.id == sid for s in t.subtopics))

    # 1. update mastery (evidence only: a pass lifts it to at least the score, a fail moves it
    #    halfway; a pass also promotes the level, a fail keeps it)
    mastery = _mastery_map(enr)
    by_sub = []
    for sid, p in per.items():
        rec = mastery.get(sid) or _new_mastery(enr, sid)
        before, level_before = rec.score, rec.level
        rec.attempts += 1
        rec.studied = True
        rec.last_score = p["score"]
        if p["score"] >= thr:
            rec.score = max(before, p["score"])
            rec.needs_review = False
            rec.level = next_level(rec.level)
        else:
            rec.score = max(before, js_round((before + p["score"]) / 2))
        by_sub.append({
            "subtopic_id": sid, "title": sub_title.get(sid, ""), "score": p["score"],
            "correct": p["correct"], "total": p["total"], "before": before, "after": rec.score,
            "level": rec.level, "promoted": rec.level != level_before,
        })

    result = f"{score}%"
    actions = {"failed": not passed, "items": [], "shifted": 0}
    is_topic = kind == "topic"

    def planned_quiz() -> Task | None:
        if is_topic:
            return next((t for t in tasks if not t.done and t.type == "topic_quiz" and t.topic_id == topic_id), None)
        return next((t for t in tasks if not t.done and t.type in QUIZ_LIKE and t.subtopic_id == subtopic_id), None)

    if passed:
        if is_topic:
            for t in tasks:
                if not t.done and t.type == "topic_quiz" and t.topic_id == topic_id:
                    done(t, result)
        else:
            for t in tasks:
                if not t.done and t.type in QUIZ_LIKE and t.subtopic_id == subtopic_id:
                    done(t, result)
            tasks[:] = [t for t in tasks if t.done or not (t.type == "remediation" and t.subtopic_id == subtopic_id)]
        if not any(not t.done for t in tasks):
            _add_notice(enr, "info", "Every task in your plan is complete.")
    else:
        # 2. adaptive logic: reschedule, add remediation, recalculate
        failing = [b for b in by_sub if b["score"] < thr] if is_topic else list(by_sub)
        if not failing:
            failing = [min(by_sub, key=lambda b: b["score"])]
        failing_ids = {f["subtopic_id"] for f in failing}
        for sid in failing_ids:
            mastery[sid].needs_review = True
        planned = planned_quiz()
        if planned:
            done(planned, f"{result} · below threshold")
        tasks[:] = [
            t for t in tasks
            if t.done or not (
                (t.subtopic_id in failing_ids and (t.type in QUIZ_LIKE or t.type == "remediation"))
                or (is_topic and t.type == "topic_quiz" and t.topic_id == topic_id)
            )
        ]
        anchor = next(t for t in course.topics if t.id == topic_id) if is_topic else topic_of(subtopic_id)
        extra = [
            make_task("remediation", topic_of(f["subtopic_id"]).id, f["subtopic_id"],
                      f"Remediation: {f['title']}", MINUTES["remediation"])
            for f in failing
        ]
        extra.append(
            make_task("topic_quiz", anchor.id, None, f"Retake topic quiz: {anchor.title}", MINUTES["topic_quiz"])
            if is_topic else
            make_task("retake", anchor.id, subtopic_id, f"Retake quiz: {sub_title[subtopic_id]}", MINUTES["retake"])
        )
        insert_later(tasks, extra, anchor.id, 2 if is_topic else 3)
        if is_topic:
            move_topic_quiz_last(tasks, anchor.id)  # a retaken topic quiz still comes last in its topic
        actions["shifted"] = schedule(enr, tasks).moved
        actions["items"] = [{"title": t.title, "type": t.type, "date": t.scheduled_for, "day": (t.day or 0) + 1}
                            for t in extra]
        retake, shifted = extra[-1], actions["shifted"]
        label = ctx["title"].split(": ", 1)[-1]
        rest = (f"{shifted} later {'task was' if shifted == 1 else 'tasks were'} shifted to rebalance the plan."
                if shifted else "The rest of the plan was recalculated.")
        _add_notice(enr, "reschedule",
                    f"Scored {score}% on {label}, below the {thr}% threshold. "
                    f"{', '.join(f['title'] for f in failing)} moved to later in the plan with remediation "
                    f"material; retake scheduled for Day {(retake.day or 0) + 1}. {rest}")

    _save_tasks(enr, tasks)
    breakdown = [{"subtopic_id": b["subtopic_id"], "score": b["score"], "correct": b["correct"],
                  "total": b["total"]} for b in by_sub]
    _attempt(enr, ctx, passed, thr, breakdown)
    db.flush()
    day_status = _check_days(enr, course, touched)
    db.commit()
    request_replan(db, enr, user.id, (
        f"The student failed a quiz ({score}%, pass mark {thr}%); give the weak sub-topics more time."
        if not passed else f"The student passed a quiz with {score}%; rebalance the time that is left."))
    nxt = next((t for t in enr.tasks if t.status != "done"), None)
    return {
        "kind": kind, "course_id": course.id, "title": ctx["title"], "score": score,
        "correct": ctx["correct"], "total": ctx["total"], "passed": passed, "threshold": thr,
        "review": ctx["review"], "by_subtopic": by_sub, "actions": actions,
        "day_status": metrics.status_out(day_status) if day_status else None,
        "next_task": ({"id": nxt.id, "title": nxt.title, "type": nxt.type, "date": nxt.scheduled_for,
                       "subtopic_id": nxt.subtopic_id, "topic_id": nxt.topic_id} if nxt else None),
        "plan": None,
    }


# ------------------------------------------------------------ plan & tasks


def complete_task(db: Session, user: User, course_id: str, task_id: str) -> dict:
    course = _course(db, course_id)
    enr = _must_enrollment(db, user, course)
    t = next((x for x in enr.tasks if x.id == task_id), None)
    if t is None:
        raise LearningError("Task not found.", 404)
    if t.type not in ("study", "remediation"):
        raise LearningError("Quizzes are completed by taking them.")
    if t.status != "done":
        t.status, t.completed_at, t.result = "done", clock.now(), "completed"
        rec = _mastery_map(enr).get(t.subtopic_id)
        if rec:
            rec.studied = True
    db.flush()
    status = _check_days(enr, course, {t.day_index})
    db.commit()
    return {"task_id": task_id, "day_status": metrics.status_out(status) if status else None}


def complete_subtopic_task(db: Session, user: User, course_id: str, subtopic_id: str, type_: str) -> dict:
    """Marks the first pending study/remediation task of a sub-topic as done ("Mark as studied")."""
    course = _course(db, course_id)
    enr = _must_enrollment(db, user, course)
    t = next((x for x in enr.tasks if x.status != "done" and x.subtopic_id == subtopic_id and x.type == type_), None)
    if t is None:
        rec = _mastery_map(enr).get(subtopic_id)
        if rec:
            rec.studied = True
        db.commit()
        return {"task_id": None, "day_status": None}
    return complete_task(db, user, course_id, t.id)


def update_plan_settings(db: Session, user: User, course_id: str, minutes: int | None,
                         days: int | None) -> dict:
    if minutes is None and days is None:
        raise LearningError("Choose a daily study time or a time frame.")
    if minutes is not None and minutes not in MINUTES_OPTIONS:
        raise LearningError("Choose a daily study time from the list.")
    if days is not None and days not in DAYS_OPTIONS:
        raise LearningError("Choose a time frame from the list.")
    course = _course(db, course_id)
    enr = _must_enrollment(db, user, course)
    enr.minutes_per_day = minutes or enr.minutes_per_day
    enr.target_days = days or enr.target_days
    tasks = _to_tasks(enr)
    moved = schedule(enr, tasks).moved
    _save_tasks(enr, tasks)
    tail = f" and {moved} {'task moved' if moved == 1 else 'tasks moved'} later" if moved else ""
    what = (f"Daily study time set to {enr.minutes_per_day} minutes" if days is None else
            f"Plan set to {enr.minutes_per_day} minutes a day over {enr.target_days} days")
    _add_notice(enr, "recalc", f"{what}. The remaining plan was recalculated{tail}.")
    db.commit()
    request_replan(db, enr, user.id, "The student changed their daily study time or time frame.")
    return metrics.enrollment_detail(db, enr, course)


# ------------------------------------------------------- reads for the UI


def catalog(db: Session, user: User) -> list[dict]:
    items = course_svc.catalog(db)
    enrs = {e.course_id: e for e in db.scalars(select(Enrollment).where(Enrollment.user_id == user.id))}
    for item in items:
        enr = enrs.get(item["id"])
        if enr:
            course = course_repo.get_with_tree(db, item["id"])
            refresh(db, enr, course)
            item["enrollment"] = metrics.enrollment_summary(db, enr, course)
        else:
            item["enrollment"] = None
    return items


def student_course(db: Session, user: User, course_id: str) -> dict:
    out = course_svc.course_structure(db, course_id)
    enr = get_enrollment(db, user, course_id)
    if enr:
        course = course_repo.get_with_tree(db, course_id)
        refresh(db, enr, course)
        out["enrollment"] = metrics.enrollment_detail(db, enr, course)
    else:
        out["enrollment"] = None
    return out


def subtopic_view(db: Session, user: User, course_id: str, subtopic_id: str) -> dict:
    """Sub-topic content plus the student's own mastery and plan tasks for it (when enrolled).

    Flashcards are shown at the student's current level for this sub-topic (beginner if not enrolled).
    """
    enr = get_enrollment(db, user, course_id)
    rec = _mastery_map(enr).get(subtopic_id) if enr else None
    try:
        out = course_svc.subtopic_view(db, course_id, subtopic_id, rec.level if rec else "beginner")
    except course_svc.CourseError as e:
        raise LearningError(e.message, e.status_code) from e
    out["mastery"], out["tasks"] = None, []
    if enr:
        course = course_repo.get_with_tree(db, course_id)
        refresh(db, enr, course)
        rec = _mastery_map(enr).get(subtopic_id)
        if rec:
            out["mastery"] = {
                "value": rec.score, "last_score": rec.last_score, "attempts": rec.attempts,
                "remediation": rec.needs_review, "studied": rec.studied, "level": rec.level,
                "status": metrics.sub_status(rec, out["threshold"]),
            }
        out["tasks"] = [metrics.task_out(t) for t in enr.tasks if t.subtopic_id == subtopic_id]
    return out


def _my_enrollments(db: Session, user: User) -> list[tuple[Enrollment, Course]]:
    pairs = []
    for enr in db.scalars(select(Enrollment).where(Enrollment.user_id == user.id).order_by(Enrollment.created_at)):
        course = course_repo.get_with_tree(db, enr.course_id)
        refresh(db, enr, course)
        pairs.append((enr, course))
    return pairs


def dashboard(db: Session, user: User) -> dict:
    pairs = _my_enrollments(db, user)
    summaries = [metrics.enrollment_summary(db, e, c) for e, c in pairs]
    statuses = sorted(
        ({**metrics.status_out(d), "course_id": c.id, "course_code": c.code}
         for e, c in pairs for d in e.day_statuses),
        key=lambda s: s["created_at"], reverse=True,
    )[:4]
    recent = sorted(
        ({**metrics.attempt_out(a), "course_id": c.id} for e, c in pairs for a in e.attempts),
        key=lambda a: a["created_at"], reverse=True,
    )[:5]
    return {
        "enrollments": summaries,
        "today": [
            {**t, "course_id": s["course_id"], "course_code": s["code"], "course_title": s["title"]}
            for s in summaries for t in s["today_tasks"]
        ],
        "statuses": statuses,
        "recent": recent,
    }


def progress(db: Session, user: User) -> dict:
    return {"enrollments": [metrics.enrollment_detail(db, e, c) for e, c in _my_enrollments(db, user)]}


def practice_options(db: Session, user: User) -> list[dict]:
    out = []
    for enr, course in _my_enrollments(db, user):
        thr = threshold_for(db, course)
        mastery = _mastery_map(enr)
        out.append({
            "course_id": course.id, "code": course.code, "title": course.title,
            "subtopics": [
                {"id": s.id, "title": s.title, "topic": t.title,
                 "mastery": mastery[s.id].score if s.id in mastery else 0,
                 "status": metrics.sub_status(mastery.get(s.id), thr)}
                for t, s in all_subtopics(course)
            ],
        })
    return out


def history(db: Session, user: User) -> list[dict]:
    """Every quiz attempt, newest first, grouped by course, with the per-sub-topic breakdown."""
    out = []
    for enr, course in _my_enrollments(db, user):
        titles = {s.id: s.title for _, s in all_subtopics(course)}
        out.append({
            "course_id": course.id, "code": course.code, "title": course.title,
            "attempts": [
                {**metrics.attempt_out(a), "course_id": course.id,
                 "breakdown": [{**b, "title": titles.get(b["subtopic_id"], "")} for b in a.breakdown]}
                for a in reversed(enr.attempts)
            ],
        })
    return out
