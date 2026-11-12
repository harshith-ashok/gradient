from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core import clock
from app.models import Course, Mastery, QuizAttempt, QuizSession, Setting

FATIMA = ("fatima.khan@gradient.edu", "student123", "student")
MEERA = ("meera.iyer@gradient.edu", "student123", "student")
RAO = ("ananya.rao@gradient.edu", "faculty123", "staff")
C = "c-cs101"
API = "/api/v1/student"


# --------------------------------------------------------------- helpers


def sheet(db, quiz_id, right=lambda q: True):
    """Answers for an open quiz. `right(question)` decides which ones are answered correctly."""
    out = {}
    for q in db.get(QuizSession, quiz_id).questions:
        out[q["id"]] = q["answer"] if right(q) else (q["answer"] + 1) % len(q["options"])
    return out


def start(c, course=C, kind="pretest", **kw):
    return c.post(f"{API}/quizzes", json={"course_id": course, "kind": kind, **kw})


def take(c, db, course=C, kind="pretest", right=lambda q: True, **kw):
    r = start(c, course, kind, **kw)
    assert r.status_code == 200, r.text
    quiz = r.json()
    res = c.post(f"{API}/quizzes/{quiz['quiz_id']}/submit", json={"answers": sheet(db, quiz["quiz_id"], right)})
    assert res.status_code == 200, res.text
    return res.json()


def enroll(c, db, course=C, right=lambda q: False):
    return take(c, db, course, "pretest", right)


def detail(c, course=C):
    return c.get(f"{API}/courses/{course}").json()["enrollment"]


def tasks_of(c, course=C):
    return detail(c, course)["tasks"]


@pytest.fixture
def fatima(as_user):
    return as_user(*FATIMA)


# ---------------------------------------------------------------- pre-test


def test_pretest_hides_answers_and_covers_every_subtopic(fatima):
    r = start(fatima)
    assert r.status_code == 200
    quiz = r.json()
    assert quiz["threshold"] is None and quiz["kind"] == "pretest"
    assert len(quiz["questions"]) == 12  # 6 sub-topics x 2
    assert all(set(q) == {"id", "text", "options"} for q in quiz["questions"])


def test_pretest_all_wrong_builds_a_full_study_plan(fatima, db):
    res = enroll(fatima, db)
    assert res["score"] == 0 and res["passed"] is None
    assert res["plan"]["tasks"] == 14 and res["plan"]["minutes_per_day"] == 60
    enr = detail(fatima)
    types = [t["type"] for t in enr["tasks"]]
    assert types.count("study") == 6 and types.count("quiz") == 6 and types.count("topic_quiz") == 2
    assert "confirm" not in types
    assert all(t["minutes"] == 30 for t in enr["tasks"] if t["type"] == "study")  # nothing known yet
    assert enr["overall"] == 0 and enr["status"] == "on-track" and enr["day_number"] == 1
    assert enr["today"] == clock.today().isoformat()
    assert enr["notices"][0]["kind"] == "info" and "6 sub-topics need full study" in enr["notices"][0]["text"]


def test_pretest_all_right_only_needs_confirmation_quizzes(fatima, db):
    res = enroll(fatima, db, right=lambda q: True)
    assert res["score"] == 100
    enr = detail(fatima)
    types = [t["type"] for t in enr["tasks"]]
    assert types.count("confirm") == 6 and types.count("topic_quiz") == 2 and "study" not in types
    assert enr["overall"] == 50  # mastery starts at half the pre-test score
    assert {s["level"] for t in enr["topic_detail"] for s in t["subtopics"]} == {"intermediate"}


def test_plan_respects_daily_budget_and_syllabus_order(fatima, db):
    enroll(fatima, db)
    tasks = tasks_of(fatima)
    per_day: dict[int, int] = {}
    for t in tasks:
        per_day[t["day"]] = per_day.get(t["day"], 0) + t["minutes"]
    assert all(m <= 60 for m in per_day.values())
    assert [t["day"] for t in tasks] == sorted(t["day"] for t in tasks)
    first_topic = [t for t in tasks if t["topic_id"] == "c-t1"]
    second_topic = [t for t in tasks if t["topic_id"] == "c-t2"]
    assert max(t["day"] for t in first_topic) <= min(t["day"] for t in second_topic)
    assert tasks[0]["date"] == clock.today().isoformat()


def test_cannot_sit_the_pretest_twice(fatima, db):
    enroll(fatima, db)
    r = start(fatima)
    assert r.status_code == 400 and "already taken" in r.json()["detail"]


def test_enrollment_shows_in_catalog_and_course_page(fatima, db):
    assert fatima.get(f"{API}/courses/{C}").json()["enrollment"] is None
    enroll(fatima, db)
    cat = {c["id"]: c for c in fatima.get(f"{API}/catalog").json()}
    assert cat[C]["enrollment"]["pending_count"] == 14 and cat["econ-101"]["enrollment"] is None


def test_pretest_is_stored_as_an_attempt(fatima, db):
    enroll(fatima, db)
    a = db.scalars(select(QuizAttempt)).one()
    assert a.kind == "pretest" and a.passed is None and a.pass_mark is None and a.total == 12
    assert len(a.breakdown) == 6 and len(a.answers) == 12


# ------------------------------------------------------- mastery and levels


def test_pass_lifts_mastery_and_promotes_level(fatima, db):
    enroll(fatima, db)
    res = take(fatima, db, kind="subtopic", subtopic_id="c-vars")
    sub = res["by_subtopic"][0]
    assert res["passed"] is True and sub["score"] == 100 and sub["after"] == 100
    assert sub["level"] == "intermediate" and sub["promoted"] is True
    again = take(fatima, db, kind="subtopic", subtopic_id="c-vars")
    assert again["by_subtopic"][0]["level"] == "advanced"


def test_level_is_capped_at_expert(fatima, db):
    enroll(fatima, db)
    for _ in range(6):
        res = take(fatima, db, kind="practice", subtopic_id="c-vars")
    assert res["by_subtopic"][0]["level"] == "expert"


def test_fail_moves_mastery_halfway_and_keeps_level(fatima, db):
    enroll(fatima, db)
    m = db.scalar(select(Mastery).where(Mastery.subtopic_id == "c-vars"))
    m.score, m.level = 10, "advanced"
    db.commit()
    # 1 of 4 right = 25%, below the 70% pass mark
    seen = iter(range(4))
    res = take(fatima, db, kind="subtopic", subtopic_id="c-vars", right=lambda q: next(seen) == 0)
    sub = res["by_subtopic"][0]
    assert res["passed"] is False and sub["score"] == 25
    assert sub["after"] == 18  # halfway from 10 to 25, rounded half up (17.5)
    assert sub["level"] == "advanced" and sub["promoted"] is False


def test_fail_never_lowers_mastery(fatima, db):
    enroll(fatima, db)
    m = db.scalar(select(Mastery).where(Mastery.subtopic_id == "c-vars"))
    m.score = 80
    db.commit()
    res = take(fatima, db, kind="subtopic", subtopic_id="c-vars", right=lambda q: False)
    assert res["by_subtopic"][0]["after"] == 80


# --------------------------------------------------------------- adaptive


def test_failing_a_quiz_reschedules_adds_remediation_and_recalculates(fatima, db):
    enroll(fatima, db)
    before = tasks_of(fatima)
    res = take(fatima, db, kind="subtopic", subtopic_id="c-vars", right=lambda q: False)
    assert res["passed"] is False and res["actions"]["failed"] is True
    assert [i["type"] for i in res["actions"]["items"]] == ["remediation", "retake"]

    after = tasks_of(fatima)
    vars_tasks = [t for t in after if t["subtopic_id"] == "c-vars"]
    kinds = {t["type"]: t for t in vars_tasks}
    # the planned quiz was used up and marked, and exactly one retake + one remediation exist
    assert kinds["quiz"]["done"] and kinds["quiz"]["result"] == "0% · below threshold"
    assert sum(t["type"] == "retake" for t in vars_tasks) == 1
    assert sum(t["type"] == "remediation" for t in vars_tasks) == 1
    assert not kinds["retake"]["done"] and not kinds["remediation"]["done"]
    order = [t["type"] for t in after if t["subtopic_id"] == "c-vars"]
    assert order.index("remediation") < order.index("retake")
    assert len(after) == len(before) + 2  # remediation + retake added

    # the sub-topic is flagged and the plan explains what happened
    enr = detail(fatima)
    sub = next(s for t in enr["topic_detail"] for s in t["subtopics"] if s["id"] == "c-vars")
    assert sub["status"] == "review" and enr["status"] == "attention" and enr["remediation_count"] == 1
    note = enr["notices"][0]
    assert note["kind"] == "reschedule" and "below the 70% threshold" in note["text"]
    assert "retake scheduled" in note["text"]

    # the rest of the plan was recalculated within the daily budget
    per_day: dict[int, int] = {}
    for t in after:
        per_day[t["day"]] = per_day.get(t["day"], 0) + t["minutes"]
    assert all(m <= 60 for m in per_day.values())
    assert res["actions"]["shifted"] >= 1


def test_passing_the_retake_completes_it_and_clears_remediation(fatima, db):
    enroll(fatima, db)
    take(fatima, db, kind="subtopic", subtopic_id="c-vars", right=lambda q: False)
    res = take(fatima, db, kind="subtopic", subtopic_id="c-vars")
    assert res["passed"] is True
    vt = [t for t in tasks_of(fatima) if t["subtopic_id"] == "c-vars"]
    assert not any(t["type"] == "remediation" and not t["done"] for t in vt)  # unneeded help removed
    assert all(t["done"] for t in vt if t["type"] in ("quiz", "retake"))
    enr = detail(fatima)
    sub = next(s for t in enr["topic_detail"] for s in t["subtopics"] if s["id"] == "c-vars")
    assert sub["status"] == "mastered" and enr["remediation_count"] == 0


def test_repeated_failures_do_not_pile_up_duplicate_tasks(fatima, db):
    enroll(fatima, db)
    for _ in range(3):
        take(fatima, db, kind="subtopic", subtopic_id="c-vars", right=lambda q: False)
    vt = [t for t in tasks_of(fatima) if t["subtopic_id"] == "c-vars" and not t["done"]]
    # exactly one remediation and one retake, however often the quiz was failed (study is still pending)
    assert sorted(t["type"] for t in vt) == ["remediation", "retake", "study"]


def test_failing_a_topic_quiz_only_flags_the_weak_subtopics(fatima, db):
    enroll(fatima, db)
    res = take(fatima, db, kind="topic", topic_id="c-t1", right=lambda q: q["subtopic_id"] == "c-vars")
    assert res["passed"] is False
    flagged = {t["subtopic_id"] for t in tasks_of(fatima) if t["type"] == "remediation" and not t["done"]}
    assert flagged == {"c-flow", "c-func"}  # c-vars was answered correctly
    types = [t["type"] for t in tasks_of(fatima) if t["topic_id"] == "c-t1" and not t["done"]]
    assert types[-1] == "topic_quiz"  # the retake stays after the other work in that topic


def test_passing_a_topic_quiz_completes_it(fatima, db):
    enroll(fatima, db)
    res = take(fatima, db, kind="topic", topic_id="c-t1")
    assert res["passed"] is True
    tq = next(t for t in tasks_of(fatima) if t["type"] == "topic_quiz" and t["topic_id"] == "c-t1")
    assert tq["done"] and tq["result"] == "100%"


def test_on_demand_quiz_works_for_any_subtopic(fatima, db):
    assert start(fatima, kind="practice", subtopic_id="c-vars").status_code == 404  # not enrolled yet
    enroll(fatima, db)
    res = take(fatima, db, kind="practice", subtopic_id="c-ptr")
    assert res["title"].startswith("Practice quiz:") and res["passed"] is True
    assert start(fatima, kind="practice", subtopic_id="nope").status_code == 404


# ------------------------------------------------------------- pass marks


def test_course_pass_mark_override_changes_the_outcome(fatima, db):
    enroll(fatima, db)
    db.get(Course, C).pass_mark = 100
    db.commit()
    seen = iter(range(4))
    res = take(fatima, db, kind="subtopic", subtopic_id="c-vars", right=lambda q: next(seen) != 0)  # 75%
    assert res["threshold"] == 100 and res["passed"] is False


def test_global_pass_mark_applies_when_no_override(fatima, db):
    enroll(fatima, db)
    db.get(Setting, "pass_mark").value = 50
    db.commit()
    seen = iter(range(4))
    res = take(fatima, db, kind="subtopic", subtopic_id="c-vars", right=lambda q: next(seen) < 2)  # 50%
    assert res["threshold"] == 50 and res["passed"] is True


def test_pass_mark_is_inclusive(fatima, db):
    enroll(fatima, db)
    db.get(Setting, "pass_mark").value = 75
    db.commit()
    seen = iter(range(4))
    res = take(fatima, db, kind="subtopic", subtopic_id="c-vars", right=lambda q: next(seen) < 3)  # 75%
    assert res["score"] == 75 and res["passed"] is True


# ----------------------------------------------------- day status / calendar


def test_day_status_appears_when_a_day_is_finished(fatima, db):
    enroll(fatima, db, right=lambda q: True)  # all confirmation quizzes: 15 min each, 4 per day
    day0 = [t for t in tasks_of(fatima) if t["day"] == 0]
    assert len(day0) >= 2
    last = None
    for t in day0:
        last = take(fatima, db, kind="subtopic", subtopic_id=t["subtopic_id"])
    assert last["day_status"]["message"].startswith("Day 1 completed – ")
    assert last["day_status"]["day"] == 1
    assert detail(fatima)["latest_day_status"]["message"] == last["day_status"]["message"]


def test_study_tasks_complete_without_a_quiz(fatima, db):
    enroll(fatima, db)
    t = next(t for t in tasks_of(fatima) if t["type"] == "study")
    r = fatima.post(f"{API}/courses/{C}/tasks/{t['id']}/complete")
    assert r.status_code == 200 and r.json()["task_id"] == t["id"]
    assert next(x for x in tasks_of(fatima) if x["id"] == t["id"])["done"]
    quiz = next(t for t in tasks_of(fatima) if t["type"] == "quiz")
    assert fatima.post(f"{API}/courses/{C}/tasks/{quiz['id']}/complete").status_code == 400
    assert fatima.post(f"{API}/courses/{C}/tasks/nope/complete").status_code == 404


def test_mark_studied_by_subtopic(fatima, db):
    enroll(fatima, db)
    sid = next(t for t in tasks_of(fatima) if t["type"] == "study")["subtopic_id"]
    r = fatima.post(f"{API}/courses/{C}/subtopics/{sid}/complete", json={"type": "study"})
    assert r.status_code == 200 and r.json()["task_id"]
    view = fatima.get(f"{API}/courses/{C}/subtopics/{sid}").json()
    assert view["mastery"]["studied"] is True and view["mastery"]["status"] == "learning"
    assert any(t["type"] == "study" and t["done"] for t in view["tasks"])


def test_missed_days_roll_forward_and_the_plan_is_recalculated(fatima, db):
    with clock.days_ago(3):
        enroll(fatima, db)
        original = tasks_of(fatima)
    assert min(t["day"] for t in original) == 0
    enr = detail(fatima)  # today is now 3 days after the plan started
    today = clock.today().isoformat()
    open_tasks = [t for t in enr["tasks"] if not t["done"]]
    assert all(t["day"] >= 3 for t in open_tasks) and open_tasks[0]["date"] == today
    assert enr["day_number"] == 4
    assert any(n["kind"] == "recalc" and "moved forward" in n["text"] for n in enr["notices"])
    # idempotent: reading again does not add another notice
    assert len([n for n in detail(fatima)["notices"] if n["kind"] == "recalc"]) == 1


def test_changing_daily_minutes_repacks_the_plan(fatima, db):
    enroll(fatima, db)
    days_before = len({t["day"] for t in tasks_of(fatima)})
    r = fatima.put(f"{API}/courses/{C}/plan", json={"minutes_per_day": 120})
    assert r.status_code == 200
    body = r.json()
    assert body["minutes_per_day"] == 120 and len({t["day"] for t in body["tasks"]}) < days_before
    assert "Daily study time set to 120 minutes" in body["notices"][0]["text"]
    assert fatima.put(f"{API}/courses/{C}/plan", json={"minutes_per_day": 17}).status_code == 400


# ------------------------------------------------------- quiz sessions


def test_a_quiz_can_only_be_submitted_once(fatima, db):
    enroll(fatima, db)
    quiz = start(fatima, kind="practice", subtopic_id="c-vars").json()
    body = {"answers": sheet(db, quiz["quiz_id"])}
    assert fatima.post(f"{API}/quizzes/{quiz['quiz_id']}/submit", json=body).status_code == 200
    assert fatima.post(f"{API}/quizzes/{quiz['quiz_id']}/submit", json=body).status_code == 410


def test_quizzes_belong_to_their_owner(fatima, as_user, db):
    enroll(fatima, db)
    quiz = start(fatima, kind="practice", subtopic_id="c-vars").json()
    meera = as_user(*MEERA)
    r = meera.post(f"{API}/quizzes/{quiz['quiz_id']}/submit", json={"answers": {}})
    assert r.status_code == 410
    assert db.get(QuizSession, quiz["quiz_id"]) is not None  # not consumed by someone else


def test_expired_quiz_is_rejected(fatima, db):
    enroll(fatima, db)
    quiz = start(fatima, kind="practice", subtopic_id="c-vars").json()
    sess = db.get(QuizSession, quiz["quiz_id"])
    sess.created_at = clock.now() - timedelta(hours=3)
    db.commit()
    r = fatima.post(f"{API}/quizzes/{quiz['quiz_id']}/submit", json={"answers": sheet(db, quiz["quiz_id"])})
    assert r.status_code == 410 and "expired" in r.json()["detail"]


def test_unanswered_and_invalid_answers_count_as_wrong(fatima, db):
    enroll(fatima, db)
    quiz = start(fatima, kind="practice", subtopic_id="c-vars").json()
    ids = [q["id"] for q in quiz["questions"]]
    r = fatima.post(f"{API}/quizzes/{quiz['quiz_id']}/submit", json={"answers": {ids[0]: 99}})
    assert r.status_code == 200 and r.json()["score"] == 0
    assert all(item["chosen"] in (None, 99) for item in r.json()["review"])


def test_review_reveals_answers_only_after_submitting(fatima, db):
    enroll(fatima, db)
    res = take(fatima, db, kind="practice", subtopic_id="c-vars")
    assert all(item["explanation"] and 0 <= item["answer"] < len(item["options"]) for item in res["review"])


def test_unknown_course_and_bad_requests(fatima):
    assert start(fatima, course="nope").status_code == 404
    assert start(fatima, kind="topic", topic_id="x").status_code == 404  # not enrolled
    assert fatima.post(f"{API}/quizzes", json={"course_id": C, "kind": "weird"}).status_code == 422


# ------------------------------------------------------ history / reads


def test_every_attempt_is_saved_and_shown_newest_first(fatima, db):
    enroll(fatima, db)
    take(fatima, db, kind="practice", subtopic_id="c-vars", right=lambda q: False)
    take(fatima, db, kind="practice", subtopic_id="c-vars")
    rows = db.scalars(select(QuizAttempt).order_by(QuizAttempt.created_at)).all()
    assert [r.kind for r in rows] == ["pretest", "practice", "practice"]
    assert rows[1].passed is False and rows[1].pass_mark == 70 and rows[2].passed is True
    hist = detail(fatima)["history"]
    assert [h["kind"] for h in hist] == ["practice", "practice", "pretest"]
    assert hist[0]["score"] == 100 and hist[1]["score"] == 0


def test_dashboard_progress_and_practice_options(fatima, db):
    assert fatima.get(f"{API}/dashboard").json()["enrollments"] == []
    enroll(fatima, db)
    take(fatima, db, kind="practice", subtopic_id="c-vars")
    d = fatima.get(f"{API}/dashboard").json()
    assert len(d["enrollments"]) == 1 and d["recent"][0]["kind"] == "practice"
    assert d["today"] and d["today"][0]["course_code"] == "CS 101"
    p = fatima.get(f"{API}/progress").json()["enrollments"]
    assert len(p) == 1 and p[0]["topic_detail"][0]["subtopics"]
    opts = fatima.get(f"{API}/practice").json()
    assert opts[0]["course_id"] == C and len(opts[0]["subtopics"]) == 6


def test_students_only_see_their_own_data(fatima, as_user, db):
    enroll(fatima, db)
    meera = as_user(*MEERA)
    assert meera.get(f"{API}/courses/{C}").json()["enrollment"] is None
    assert meera.get(f"{API}/progress").json()["enrollments"] == []


def test_staff_cannot_use_learning_routes(as_user):
    c = as_user(*RAO)
    assert c.post(f"{API}/quizzes", json={"course_id": C, "kind": "pretest"}).status_code == 403
    assert c.get(f"{API}/dashboard").status_code == 403


def test_anonymous_gets_401(client):
    assert client.get(f"{API}/dashboard").status_code == 401
    assert client.post(f"{API}/quizzes", json={"course_id": C, "kind": "pretest"}).status_code == 401


# ------------------------------------------------------------ seed history


def test_demo_history_reproduces_the_prototype_scenarios(db, as_user):
    from app.seed import run as seed

    assert seed.run(db)["history"] == 8
    assert seed.run(db)["history"] == 0  # idempotent
    meera = as_user(*MEERA)
    enr = detail(meera)
    kinds = [(h["kind"], h["passed"]) for h in enr["history"]]
    assert ("subtopic", False) in kinds  # S1: one failed quiz...
    assert any(n["kind"] == "reschedule" for n in enr["notices"])  # ...and its reschedule
    assert any(t["type"] == "remediation" for t in enr["tasks"]) and any(t["type"] == "retake" for t in enr["tasks"])
    assert enr["day_statuses"] and enr["day_statuses"][0]["message"].startswith("Day ")
    fatima = as_user(*FATIMA)
    assert fatima.get(f"{API}/progress").json()["enrollments"] == []  # S2: new student, no courses yet
    assert fatima.get(f"{API}/catalog").json()[0]["enrollment"] is None
