import pytest
from sqlalchemy import event, select

from app.models import Course
from tests.test_learning import enroll, sheet, start

ADMIN = ("richard.hale@gradient.edu", "admin123", "staff")
RAO = ("ananya.rao@gradient.edu", "faculty123", "staff")
MEERA = ("meera.iyer@gradient.edu", "student123", "student")
FATIMA = ("fatima.khan@gradient.edu", "student123", "student")
API = "/api/v1/admin"


@pytest.fixture
def seeded(db):
    """The demo database including the replayed student history."""
    from app.seed import run as seed

    seed.run(db)
    return db


@pytest.fixture
def admin(as_user):
    return as_user(*ADMIN)


# ------------------------------------------------------------------ access


@pytest.mark.parametrize("path", ["/overview", "/settings", "/students/u-meera"])
def test_admin_routes_are_admin_only(as_user, client, path):
    assert client.get(API + path).status_code == 401
    assert as_user(*MEERA).get(API + path).status_code == 403
    assert as_user(*RAO).get(API + path).status_code == 403  # faculty are not management


def test_non_admin_cannot_change_settings(as_user):
    body = {"global_threshold": 50, "per_course": {}}
    assert as_user(*RAO).put(f"{API}/settings", json=body).status_code == 403
    assert as_user(*MEERA).put(f"{API}/settings", json=body).status_code == 403


# ---------------------------------------------------------------- overview


def test_overview_kpis_and_course_stats(seeded, admin):
    o = admin.get(f"{API}/overview").json()
    assert o["kpis"]["students"] == 7
    assert o["kpis"]["active_learners"] == 6  # Fatima has not enrolled anywhere
    assert 0 < o["kpis"]["average_progress"] <= 100
    assert o["total"] == 9  # 8 enrolments + Fatima's "not enrolled" row
    stats = {c["id"]: c for c in o["courses"]}
    assert set(stats) == {"c-cs101", "cpp-cs201", "econ-101"}
    assert stats["c-cs101"]["enrolled"] == 4 and stats["c-cs101"]["threshold"] == 70
    assert sum(c["enrolled"] for c in o["courses"]) == 8


def test_need_attention_matches_row_statuses(seeded, admin):
    o = admin.get(f"{API}/overview?page_size=100").json()
    attention = [r for r in o["rows"] if r["enrollment"] and r["enrollment"]["status"] == "attention"]
    assert o["kpis"]["need_attention"] == len(attention) >= 1  # Sofia failed quizzes and is flagged


def test_rows_carry_progress_topics_and_upcoming_tasks(seeded, admin):
    rows = admin.get(f"{API}/overview?q=meera").json()["rows"]
    assert len(rows) == 1
    e = rows[0]["enrollment"]
    assert rows[0]["student"]["student_id"] == "GU-24-0112"
    assert e["overall"] == 63 and len(e["topics"]) == 2 and e["upcoming"] and e["threshold"] == 70


def test_search_matches_name_email_and_student_id(seeded, admin):
    for term, expected in [("daniel", 2), ("OKAFOR", 2), ("gu-24-0231", 1), ("@gradient.edu", 9), ("zzz", 0)]:
        assert admin.get(f"{API}/overview", params={"q": term, "page_size": 100}).json()["total"] == expected, term


def test_course_and_status_filters(seeded, admin):
    by_course = admin.get(f"{API}/overview?course_id=c-cs101&page_size=100").json()
    assert by_course["total"] == 4
    assert {r["enrollment"]["course_id"] for r in by_course["rows"]} == {"c-cs101"}
    att = admin.get(f"{API}/overview?status=attention&page_size=100").json()
    assert att["total"] >= 1 and all(r["enrollment"]["status"] == "attention" for r in att["rows"])
    both = admin.get(f"{API}/overview?course_id=c-cs101&status=attention").json()
    assert both["total"] <= min(by_course["total"], att["total"])
    assert admin.get(f"{API}/overview?status=nonsense").status_code == 422


def test_pagination_covers_every_row_exactly_once(seeded, admin):
    seen = []
    for page in (1, 2, 3, 4):
        o = admin.get(f"{API}/overview", params={"page": page, "page_size": 3}).json()
        assert o["total"] == 9 and o["page"] == page
        seen += [(r["student"]["id"], (r["enrollment"] or {}).get("course_id")) for r in o["rows"]]
    assert len(seen) == 9 and len(set(seen)) == 9
    assert admin.get(f"{API}/overview?page=99").json()["rows"] == []
    assert admin.get(f"{API}/overview?page_size=1000").status_code == 422
    assert admin.get(f"{API}/overview?page=0").status_code == 422


def test_students_with_no_enrolment_appear_unless_filtered_by_course(seeded, admin):
    rows = admin.get(f"{API}/overview?q=fatima").json()["rows"]
    assert len(rows) == 1 and rows[0]["enrollment"] is None
    assert admin.get(f"{API}/overview?q=fatima&course_id=c-cs101").json()["total"] == 0


def _count_statements(db, fn):
    statements = []
    engine = db.get_bind()

    def count(conn, cursor, statement, *a):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        fn()
    finally:
        event.remove(engine, "before_cursor_execute", count)
    return len(statements)


def test_overview_query_count_does_not_grow_with_students(seeded, admin, db):
    """Guards against N+1: relationships are batch-loaded, so statements stay constant."""
    from app.core.security import hash_password
    from app.models import Enrollment, User

    few = _count_statements(db, lambda: admin.get(f"{API}/overview?page_size=100"))
    template = db.scalars(select(Enrollment)).first()
    for i in range(30):  # 30 more students, each enrolled in the same course
        db.add(User(id=f"x{i}", name=f"Extra {i}", email=f"x{i}@t.edu",
                    password_hash=hash_password("p"), role="student"))
        db.flush()
        db.add(Enrollment(id=f"xe{i}", user_id=f"x{i}", course_id=template.course_id,
                          plan_start_date=template.plan_start_date))
    db.commit()
    many = _count_statements(db, lambda: admin.get(f"{API}/overview?page_size=100"))
    assert many == few, f"statements grew from {few} to {many} with 30 more students (N+1)"
    assert admin.get(f"{API}/overview?page_size=100").json()["total"] == 39


def test_draft_courses_are_not_listed_in_course_stats(seeded, admin, db):
    db.get(Course, "econ-101").status = "draft"
    db.commit()
    ids = {c["id"] for c in admin.get(f"{API}/overview").json()["courses"]}
    assert "econ-101" not in ids


# ---------------------------------------------------------- student detail


def test_student_detail_has_full_progress_and_history(seeded, admin):
    d = admin.get(f"{API}/students/u-meera").json()
    assert d["student"]["name"] == "Meera Iyer" and "password_hash" not in str(d)
    e = d["enrollments"][0]
    assert e["course_id"] == "c-cs101" and len(e["history"]) == 6
    assert any(h["passed"] is False for h in e["history"]) and e["day_statuses"] and e["topic_detail"]


def test_student_detail_for_unenrolled_and_invalid_ids(seeded, admin):
    assert admin.get(f"{API}/students/u-fatima").json()["enrollments"] == []
    assert admin.get(f"{API}/students/nope").status_code == 404
    assert admin.get(f"{API}/students/u-rao").status_code == 404  # staff are not students


# ---------------------------------------------------------------- settings


def test_settings_lists_every_course_with_effective_mark(admin):
    s = admin.get(f"{API}/settings").json()
    assert s["global_threshold"] == 70 and (s["min"], s["max"]) == (40, 100)
    assert [c["code"] for c in s["courses"]] == ["CS 101", "CS 201", "ECON 101"]
    assert all(c["override"] is None and c["effective"] == 70 for c in s["courses"])


def test_save_global_and_overrides(admin):
    body = {"global_threshold": 60, "per_course": {"c-cs101": 85}}
    s = admin.put(f"{API}/settings", json=body).json()
    by = {c["id"]: c for c in s["courses"]}
    assert s["global_threshold"] == 60
    assert by["c-cs101"]["override"] == 85 and by["c-cs101"]["effective"] == 85
    assert by["econ-101"]["override"] is None and by["econ-101"]["effective"] == 60
    assert admin.get(f"{API}/settings").json() == s  # persisted


def test_saving_replaces_overrides_so_omitted_or_null_ones_clear(admin):
    admin.put(f"{API}/settings", json={"global_threshold": 70, "per_course": {"c-cs101": 90, "econ-101": 50}})
    s = admin.put(f"{API}/settings", json={"global_threshold": 70, "per_course": {"c-cs101": None}}).json()
    assert all(c["override"] is None for c in s["courses"])


@pytest.mark.parametrize("bad", [39, 101, 0, -5])
def test_pass_mark_out_of_range_is_rejected(admin, bad):
    assert admin.put(f"{API}/settings", json={"global_threshold": bad, "per_course": {}}).status_code == 400
    r = admin.put(f"{API}/settings", json={"global_threshold": 70, "per_course": {"c-cs101": bad}})
    assert r.status_code == 400 and "whole number" in r.json()["detail"]
    assert admin.get(f"{API}/settings").json()["global_threshold"] == 70  # nothing was saved


def test_boundaries_40_and_100_are_allowed(admin):
    body = {"global_threshold": 40, "per_course": {"c-cs101": 100}}
    assert admin.put(f"{API}/settings", json=body).status_code == 200


def test_non_integers_and_unknown_courses_are_rejected(admin):
    assert admin.put(f"{API}/settings", json={"global_threshold": 70.5, "per_course": {}}).status_code == 422
    assert admin.put(f"{API}/settings", json={"global_threshold": "abc", "per_course": {}}).status_code == 422
    r = admin.put(f"{API}/settings", json={"global_threshold": 70, "per_course": {"nope": 80}})
    assert r.status_code == 404


def test_new_pass_mark_applies_to_students_immediately(admin, as_user, db):
    fatima = as_user(*FATIMA)
    enroll(fatima, db)
    admin.put(f"{API}/settings", json={"global_threshold": 100, "per_course": {}})
    quiz = start(fatima, kind="practice", subtopic_id="c-vars").json()
    assert quiz["threshold"] == 100
    seen = iter(range(4))
    answers = sheet(db, quiz["quiz_id"], right=lambda q: next(seen) != 0)  # 75%
    res = fatima.post(f"/api/v1/student/quizzes/{quiz['quiz_id']}/submit", json={"answers": answers}).json()
    assert res["threshold"] == 100 and res["passed"] is False  # would have passed at 70
    assert fatima.get("/api/v1/student/courses/c-cs101").json()["threshold"] == 100


def test_changing_the_mark_while_a_quiz_is_open_grades_with_the_new_mark(admin, as_user, db):
    fatima = as_user(*FATIMA)
    enroll(fatima, db)
    quiz = start(fatima, kind="practice", subtopic_id="c-vars").json()
    admin.put(f"{API}/settings", json={"global_threshold": 40, "per_course": {"c-cs101": 100}})
    answers = sheet(db, quiz["quiz_id"])
    res = fatima.post(f"/api/v1/student/quizzes/{quiz['quiz_id']}/submit", json={"answers": answers}).json()
    assert res["threshold"] == 100 and res["passed"] is True


def test_override_changes_what_the_catalog_shows(admin, as_user):
    admin.put(f"{API}/settings", json={"global_threshold": 70, "per_course": {"c-cs101": 55}})
    cat = {c["id"]: c["threshold"] for c in as_user(*MEERA).get("/api/v1/student/catalog").json()}
    assert cat == {"c-cs101": 55, "cpp-cs201": 70, "econ-101": 70}


# ---------------------------------------------------- student history API


def test_student_history_lists_attempts_with_breakdown(seeded, as_user):
    h = as_user(*MEERA).get("/api/v1/student/history").json()
    assert len(h) == 1 and h[0]["code"] == "CS 101"
    attempts = h[0]["attempts"]
    assert len(attempts) == 6 and attempts[-1]["kind"] == "pretest"  # newest first, pre-test oldest
    pre = attempts[-1]
    assert len(pre["breakdown"]) == 6 and all(b["title"] for b in pre["breakdown"])
    topic = next(a for a in attempts if a["kind"] == "topic")
    assert len(topic["breakdown"]) == 3
    assert as_user(*FATIMA).get("/api/v1/student/history").json() == []
