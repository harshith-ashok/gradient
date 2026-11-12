"""AI study planning: the model shapes the plan, the rules guarantee it covers the course in time."""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models import Enrollment, Job, Mastery
from app.services import jobs
from app.services.pipeline import HANDLERS
from app.services.planner import MIN_FLEX, Task, apply_proposal, fit_window
from tests.test_learning import API, FATIMA, C, detail, enroll, take, tasks_of

START = date(2026, 1, 5)


def run_jobs(db):
    out = []
    while (job := jobs.claim_next(db)) is not None:
        out.append(jobs.run_job(db, job, HANDLERS))
    return out


@pytest.fixture
def fatima(as_user):
    return as_user(*FATIMA)


def t(type_, topic="T1", sub="S1", minutes=25, done=False, day=None):
    return Task(type=type_, topic_id=topic, subtopic_id=sub, title=f"{type_} {sub}", minutes=minutes,
                done=done, day=day)


def plan_of(n_subs, study=45):
    tasks = []
    for i in range(n_subs):
        tasks += [t("study", "T1", f"S{i}", study), t("quiz", "T1", f"S{i}", 15)]
    tasks.append(t("topic_quiz", "T1", None, 20))
    return tasks


# ------------------------------------------------------------ pure rules


def test_a_plan_that_already_fits_is_left_alone():
    tasks = plan_of(4)
    fit = fit_window(tasks, START, START, 60, 21)
    assert fit.fits and fit.shrunk == 0 and [x.minutes for x in tasks if x.type == "study"] == [45] * 4


def test_study_time_is_shortened_so_the_whole_syllabus_fits_the_time_frame():
    tasks = plan_of(10, study=60)  # 600 study + 150 quizzes + 20 = 770 minutes
    fit = fit_window(tasks, START, START, 60, 7)  # only 420 minutes in the window
    assert fit.fits and fit.shrunk > 0
    assert max(x.day for x in tasks) < 7
    assert len(tasks) == 21  # nothing dropped
    assert all(x.minutes >= MIN_FLEX for x in tasks if x.type == "study")
    assert all(x.minutes == 15 for x in tasks if x.type == "quiz")  # quizzes keep their length


def test_when_even_the_shortest_plan_cannot_fit_the_overrun_is_reported_not_hidden():
    tasks = plan_of(10, study=60)
    fit = fit_window(tasks, START, START, 30, 3)  # 90 minutes for a 770 minute course
    assert not fit.fits and len(tasks) == 21 and fit.last_day >= 3
    assert fit.needed_minutes_per_day > 30
    assert all(x.minutes == MIN_FLEX for x in tasks if x.type == "study")


def test_only_unfinished_tasks_are_touched_and_finished_days_count_against_the_window():
    tasks = plan_of(3)
    tasks[0].done, tasks[0].day = True, 0
    tasks[0].minutes = 45
    fit_window(tasks, START, START + timedelta(days=2), 60, 7)
    assert tasks[0].minutes == 45 and tasks[0].day == 0
    assert min(x.day for x in tasks if not x.done) == 2


def test_a_proposal_reorders_and_resizes_but_never_adds_or_removes():
    tasks = plan_of(3)
    before = sorted(x.id for x in tasks)
    apply_proposal(tasks, {"S2": {"minutes": 90, "priority": 1}, "S0": {"minutes": 10, "priority": 3},
                           "S1": {"minutes": 30, "priority": 2}, "ghost": {"minutes": 50, "priority": 1}})
    assert sorted(x.id for x in tasks) == before
    assert [x.subtopic_id for x in tasks if x.type == "study"] == ["S2", "S1", "S0"]
    assert tasks[-1].type == "topic_quiz"  # the topic quiz stays last
    assert {x.subtopic_id: x.minutes for x in tasks if x.type == "study"} == {"S2": 90, "S1": 30, "S0": 10}
    for sid in ("S0", "S1", "S2"):  # study still comes before its own quiz
        order = [x.type for x in tasks if x.subtopic_id == sid]
        assert order == ["study", "quiz"]


def test_a_proposal_never_moves_finished_work():
    tasks = plan_of(2)
    tasks[0].done = tasks[1].done = True
    first = (tasks[0].id, tasks[1].id)
    apply_proposal(tasks, {"S1": {"minutes": 20, "priority": 1}, "S0": {"minutes": 80, "priority": 2}})
    assert (tasks[0].id, tasks[1].id) == first and tasks[0].minutes == 45


# ----------------------------------------------------------- end to end


def study_minutes(c):
    return {t["subtopic_id"]: t["minutes"] for t in tasks_of(c) if t["type"] == "study"}


def test_the_plan_is_usable_immediately_and_a_planning_job_is_queued(fatima, db):
    enroll(fatima, db)
    enr = detail(fatima)
    assert enr["tasks"] and enr["planning"] is True
    assert db.scalars(select(Job).where(Job.type == "plan")).all()[0].status == "queued"


def test_the_ai_planner_gives_weak_subtopics_more_time_and_everything_stays_in_the_timeframe(fatima, db):
    # strong in variables, weak elsewhere
    res = take(fatima, db, kind="pretest", right=lambda q: q.get("subtopic_id") == "c-vars")
    assert res["by_subtopic"]
    done = run_jobs(db)
    assert [j.status for j in done] == ["succeeded"]
    enr = detail(fatima)
    assert enr["planning"] is False
    assert any(n["text"].startswith("Personalised by the AI planner") for n in enr["notices"])
    assert any(t["note"] for t in enr["tasks"])
    # coverage: every sub-topic still has its tasks, and all of it finishes inside the time frame
    subs = {s["id"] for tp in enr["topic_detail"] for s in tp["subtopics"]}
    assert {t["subtopic_id"] for t in enr["tasks"] if t["subtopic_id"]} == subs
    assert enr["plan_window"]["fits"] and max(t["day"] for t in enr["tasks"]) < enr["target_days"]


def test_a_nonsense_proposal_leaves_the_course_fully_covered(fatima, db, fake_ai):
    fake_ai.responder = lambda messages, schema: {
        "summary": "Nothing sensible comes out of this one.",
        "items": [{"subtopic_id": "made-up", "study_minutes": 90, "priority": 1, "start_level": "expert",
                   "focus": "Ignore the real syllabus."}],
    }
    enroll(fatima, db)
    before = sorted((str(t["subtopic_id"]), t["type"]) for t in tasks_of(fatima))
    assert [j.status for j in run_jobs(db)] == ["succeeded"]
    assert sorted((str(t["subtopic_id"]), t["type"]) for t in tasks_of(fatima)) == before
    assert db.scalars(select(Mastery.level)).all().count("expert") == 0


def test_the_model_cannot_start_a_student_above_what_their_pretest_supports(fatima, db, fake_ai):
    from app.agents.fake_responder import default_responder

    def greedy(messages, schema):
        out = default_responder(messages, schema)
        if schema == "PlanProposal":
            for it in out["items"]:
                it["start_level"] = "advanced"
        return out

    fake_ai.responder = greedy
    enroll(fatima, db)  # every pre-test answer wrong: score 0
    run_jobs(db)
    assert {m.level for m in db.scalars(select(Mastery)).all() if m.attempts == 0} == {"beginner"}


def test_when_the_model_is_down_the_rule_based_plan_stands(fatima, db, fake_ai):
    def down(messages, schema):
        raise RuntimeError("boom")

    fake_ai.responder = down
    enroll(fatima, db)
    before = tasks_of(fatima)
    (job,) = run_jobs(db)
    assert job.status == "failed"
    assert tasks_of(fatima) == before and detail(fatima)["planning"] is False


def test_a_failed_quiz_queues_a_replan_and_the_plan_still_fits(fatima, db):
    enroll(fatima, db)
    run_jobs(db)
    take(fatima, db, kind="subtopic", subtopic_id="c-vars", right=lambda q: False)
    queued = db.scalars(select(Job).where(Job.type == "plan", Job.status == "queued")).all()
    assert len(queued) == 1
    run_jobs(db)
    enr = detail(fatima)
    assert enr["plan_window"]["fits"]
    assert any(t["type"] == "retake" for t in enr["tasks"])


def test_replan_requests_are_not_duplicated(fatima, db):
    enroll(fatima, db)
    fatima.put(f"{API}/courses/{C}/plan", json={"minutes_per_day": 90})
    fatima.put(f"{API}/courses/{C}/plan", json={"minutes_per_day": 45})
    assert len(db.scalars(select(Job).where(Job.type == "plan")).all()) == 1


def test_a_tight_time_frame_shortens_study_and_a_hopeless_one_is_reported(fatima, db):
    enroll(fatima, db)
    full = sum(t["minutes"] for t in tasks_of(fatima))
    r = fatima.put(f"{API}/courses/{C}/plan", json={"minutes_per_day": 45, "target_days": 7})
    assert r.status_code == 200
    body = r.json()
    assert body["target_days"] == 7 and sum(t["minutes"] for t in body["tasks"]) < full
    assert body["plan_window"]["fits"] and max(t["day"] for t in body["tasks"]) < 7
    assert len(body["tasks"]) == len(tasks_of(fatima))
    assert fatima.put(f"{API}/courses/{C}/plan", json={"target_days": 5}).status_code == 400
    assert fatima.put(f"{API}/courses/{C}/plan", json={}).status_code == 400


def test_planning_can_be_switched_off(fatima, db, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "ai_planning", False)
    enroll(fatima, db)
    assert db.scalars(select(Job).where(Job.type == "plan")).all() == []
    assert db.scalars(select(Enrollment)).all()
