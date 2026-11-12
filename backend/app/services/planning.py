"""Job handler for AI study planning (run by the worker).

The student always has a working plan first: the rules build it straight after the pre-test and
after every quiz. This job then asks the model how long each sub-topic deserves, in what order, and
what to focus on, and applies that to whatever is still unfinished. The model's answer is checked
and fitted into the student's time frame, so the syllabus stays fully covered whatever it says.
"""

import logging

from sqlalchemy.orm import Session

from app.agents import planning as agent
from app.agents.llm import LLM, get_llm
from app.core import clock
from app.models import Course, Enrollment, Job
from app.services import learning
from app.services.jobs import UserFacingError, set_progress
from app.services.planner import FLEX, MIN_FLEX, RESERVE, apply_proposal, window_stats
from app.services.settings import threshold_for

log = logging.getLogger(__name__)


def _rows(enr: Enrollment, course: Course, tasks) -> list[str]:
    """One line per sub-topic that still has unfinished work."""
    mastery = learning._mastery_map(enr)
    pre = {p.subtopic_id: p.score for p in enr.pretest_results}
    pending: dict[str, list[str]] = {}
    for t in tasks:
        if not t.done and t.subtopic_id:
            pending.setdefault(t.subtopic_id, []).append(t.type)
    rows = []
    for topic in course.topics:
        for s in topic.subtopics:
            if s.id not in pending:
                continue
            m = mastery.get(s.id)
            rows.append(
                f"- {s.id} | {topic.title} | {s.title} | pretest {round(pre.get(s.id, 0))}% | "
                f"mastery {round(m.score) if m else 0}% | level {m.level if m else 'beginner'} | "
                f"attempts {m.attempts if m else 0} | last quiz "
                f"{'none' if not m or m.last_score is None else f'{round(m.last_score)}%'} | "
                f"needs review {'yes' if m and m.needs_review else 'no'} | todo {', '.join(pending[s.id])}"
            )
    return rows


def handle_plan(db: Session, job: Job, llm: LLM | None = None) -> dict:
    llm = llm or get_llm()
    enr = db.get(Enrollment, job.enrollment_id) if job.enrollment_id else None
    if enr is None:
        raise UserFacingError("This enrolment no longer exists.")
    course = db.get(Course, enr.course_id)
    thr = threshold_for(db, course)
    tasks = learning._to_tasks(enr)
    rows = _rows(enr, course, tasks)
    if not rows:
        return {"changed": False, "reason": "nothing left to plan"}
    days_left, window, fixed = window_stats(tasks, enr.plan_start_date, clock.today(),
                                            enr.minutes_per_day, enr.target_days)
    flex = sum(1 for t in tasks if not t.done and t.type in FLEX)
    budget = max(int(window * (1 - RESERVE)) - fixed, flex * MIN_FLEX)
    set_progress(db, job, "Planning your study time")
    proposal = agent.propose(llm, course=f"{course.code} {course.title}", pass_mark=thr, days_left=days_left,
                             minutes_per_day=enr.minutes_per_day, study_budget=budget, rows=rows,
                             reason=(job.params or {}).get("reason", ""))

    # The model call can take a while and the student may have studied meanwhile: re-read the plan
    # and apply the answer to what is unfinished now.
    db.expire_all()
    enr = db.get(Enrollment, job.enrollment_id)
    course = db.get(Course, enr.course_id)
    tasks = learning._to_tasks(enr)
    known = {s.id for _, s in learning.all_subtopics(course)}
    plan = agent.validate(proposal, known)

    mastery = learning._mastery_map(enr)
    pre = {p.subtopic_id: p.score for p in enr.pretest_results}
    relevel = 0
    for sid, p in plan.items():
        m = mastery.get(sid)
        # Only sub-topics the student has not started can be re-levelled, and only within what
        # their pre-test score supports.
        if m and m.attempts == 0 and not m.studied and p["level"] in agent.allowed_levels(pre.get(sid, 0), thr):
            if m.level != p["level"]:
                m.level, relevel = p["level"], relevel + 1

    apply_proposal(tasks, plan)
    for sid, p in plan.items():
        t = next((x for x in tasks if not x.done and x.subtopic_id == sid
                  and x.type in ("study", "confirm", "remediation")), None)
        if t:
            t.note = p["focus"][:200]
    fit = learning.schedule(enr, tasks)
    learning._save_tasks(enr, tasks)
    tail = (f" {fit.shrunk} study {'session was' if fit.shrunk == 1 else 'sessions were'} shortened to finish "
            f"inside your {enr.target_days}-day time frame." if fit.shrunk else "")
    learning._add_notice(enr, "info", f"Personalised by the AI planner: {proposal.summary.strip()}{tail}")
    db.commit()
    return {"changed": True, "sub_topics": len(plan), "relevelled": relevel, "shrunk": fit.shrunk,
            "fits": fit.fits}
