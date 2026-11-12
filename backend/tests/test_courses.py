import json

import pytest

from app.core import cache
from tests.conftest import login

STUDENT = ("meera.iyer@gradient.edu", "student123", "student")
RAO = ("ananya.rao@gradient.edu", "faculty123", "staff")  # owns C and C++
LEE = ("marcus.lee@gradient.edu", "faculty123", "staff")  # owns Economics
HALE = ("richard.hale@gradient.edu", "admin123", "staff")


# ---------------------------------------------------------------- students


def test_catalog_lists_published_courses(as_user):
    r = as_user(*STUDENT).get("/api/v1/student/catalog")
    assert r.status_code == 200
    courses = r.json()
    assert [c["code"] for c in courses] == ["CS 101", "CS 201", "ECON 101"]
    c = courses[0]
    assert c["topic_count"] == 2 and c["subtopic_count"] == 6
    assert c["instructor"] == "Dr. Ananya Rao" and c["threshold"] == 70


def test_catalog_hides_drafts(as_user, db):
    from app.models import Course

    db.get(Course, "econ-101").status = "draft"
    db.commit()
    codes = [c["code"] for c in as_user(*STUDENT).get("/api/v1/student/catalog").json()]
    assert "ECON 101" not in codes


def test_course_structure_has_topics_and_no_answers(as_user):
    r = as_user(*STUDENT).get("/api/v1/student/courses/c-cs101")
    body = r.json()
    assert [t["id"] for t in body["topics"]] == ["c-t1", "c-t2"]
    assert body["topics"][0]["subtopics"][0] == {
        "id": "c-vars", "title": "Variables and data types",
        "description": "Declaring variables, integer and floating-point types, type sizes and conversions.",
    }
    assert '"questions"' not in json.dumps(body) and '"answer_index"' not in json.dumps(body)


def test_unknown_or_draft_course_is_404(as_user, db):
    from app.models import Course

    c = as_user(*STUDENT)
    assert c.get("/api/v1/student/courses/nope").status_code == 404
    db.get(Course, "c-cs101").status = "draft"
    db.commit()
    assert c.get("/api/v1/student/courses/c-cs101").status_code == 404


def test_subtopic_content_and_navigation(as_user):
    c = as_user(*STUDENT)
    r = c.get("/api/v1/student/courses/c-cs101/subtopics/c-vars")
    assert r.status_code == 200
    body = r.json()
    assert body["course_code"] == "CS 101" and body["topic"]["id"] == "c-t1"
    sub = body["subtopic"]
    assert len(sub["flashcards"]) == 3 and len(sub["summary"]) == 2 and sub["points"]
    assert sub["remediation"]["steps"]
    assert body["prev"] is None and body["next"]["id"] == "c-flow"
    last = c.get("/api/v1/student/courses/c-cs101/subtopics/c-flow").json()
    assert last["prev"]["id"] == "c-vars"
    assert '"answer_index"' not in json.dumps(body) and '"questions"' not in json.dumps(body)


def test_subtopic_from_other_course_is_404(as_user):
    c = as_user(*STUDENT)
    assert c.get("/api/v1/student/courses/c-cs101/subtopics/econ-dem").status_code == 404


def test_student_routes_forbidden_to_staff(as_user):
    assert as_user(*RAO).get("/api/v1/student/catalog").status_code == 403


def test_pass_mark_override_is_reflected(as_user, db):
    from app.models import Course

    db.get(Course, "c-cs101").pass_mark = 80
    db.commit()
    c = as_user(*STUDENT)
    assert c.get("/api/v1/student/courses/c-cs101").json()["threshold"] == 80
    assert c.get("/api/v1/student/courses/c-cs101/subtopics/c-vars").json()["threshold"] == 80


# ------------------------------------------------------------------- cache


def test_structure_is_cached_and_invalidated_on_save(as_user, fake_cache):
    student, rao = as_user(*STUDENT), as_user(*RAO)
    student.get("/api/v1/student/courses/c-cs101")
    assert cache.course_key("c-cs101") in fake_cache.store
    full = rao.get("/api/v1/faculty/courses/c-cs101").json()
    full["title"] = "Programming in C (revised)"
    assert rao.put("/api/v1/faculty/courses/c-cs101", json=full).status_code == 200
    assert cache.course_key("c-cs101") not in fake_cache.store
    assert student.get("/api/v1/student/courses/c-cs101").json()["title"].endswith("(revised)")


def test_unpublish_stops_serving_cached_course(as_user, fake_cache):
    student, rao = as_user(*STUDENT), as_user(*RAO)
    student.get("/api/v1/student/courses/c-cs101")
    assert rao.post("/api/v1/faculty/courses/c-cs101/status", json={"status": "draft"}).status_code == 200
    assert student.get("/api/v1/student/courses/c-cs101").status_code == 404


def test_cache_failure_falls_back_to_database(as_user):
    class Broken:
        def get(self, *a, **k): raise ConnectionError
        def set(self, *a, **k): raise ConnectionError
        def delete(self, *a, **k): raise ConnectionError

    cache.set_backend(Broken())
    assert as_user(*STUDENT).get("/api/v1/student/courses/c-cs101").status_code == 200


# ------------------------------------------------------------------- staff


def test_faculty_sees_only_own_courses_admin_sees_all(as_user):
    rao = [c["id"] for c in as_user(*RAO).get("/api/v1/faculty/courses").json()]
    lee = [c["id"] for c in as_user(*LEE).get("/api/v1/faculty/courses").json()]
    hale = [c["id"] for c in as_user(*HALE).get("/api/v1/faculty/courses").json()]
    assert rao == ["c-cs101", "cpp-cs201"] and lee == ["econ-101"]
    assert sorted(hale) == ["c-cs101", "cpp-cs201", "econ-101"]


def test_faculty_cannot_open_or_edit_others_courses(as_user):
    rao = as_user(*RAO)
    assert rao.get("/api/v1/faculty/courses/econ-101").status_code == 403
    assert rao.put("/api/v1/faculty/courses/econ-101", json={"code": "x", "title": "x"}).status_code == 403
    assert rao.post("/api/v1/faculty/courses/econ-101/status", json={"status": "draft"}).status_code == 403
    assert as_user(*HALE).get("/api/v1/faculty/courses/econ-101").status_code == 200


def test_students_cannot_use_staff_routes(as_user):
    assert as_user(*STUDENT).get("/api/v1/faculty/courses").status_code == 403


def test_staff_get_includes_answers(as_user):
    full = as_user(*RAO).get("/api/v1/faculty/courses/c-cs101").json()
    q = full["topics"][0]["subtopics"][0]["questions"][0]
    assert q["options"][q["answer_index"]] == "3"


def test_save_roundtrip_is_lossless(as_user):
    rao = as_user(*RAO)
    full = rao.get("/api/v1/faculty/courses/c-cs101").json()
    saved = rao.put("/api/v1/faculty/courses/c-cs101", json=full).json()
    assert saved == full  # ids, order, content all preserved


def test_edit_add_remove_and_reorder(as_user):
    rao = as_user(*RAO)
    full = rao.get("/api/v1/faculty/courses/c-cs101").json()
    t1 = full["topics"][0]
    t1["subtopics"][0]["title"] = "Types"
    t1["subtopics"].reverse()
    t1["subtopics"].append({"title": "New sub-topic", "points": ["  a point  ", ""]})
    full["topics"].pop()  # remove second topic
    saved = rao.put("/api/v1/faculty/courses/c-cs101", json=full).json()
    subs = saved["topics"][0]["subtopics"]
    assert subs[-1]["title"] == "New sub-topic" and subs[-1]["id"]
    assert subs[-1]["points"] == ["a point"]
    assert subs[-2]["title"] == "Types" and subs[-2]["id"] == "c-vars"
    assert len(saved["topics"]) == 1


def test_save_validation(as_user):
    rao = as_user(*RAO)
    full = rao.get("/api/v1/faculty/courses/c-cs101").json()
    bad = {**full, "title": "  "}
    assert rao.put("/api/v1/faculty/courses/c-cs101", json=bad).status_code == 400
    full["topics"][0]["title"] = ""
    assert "needs a title" in rao.put("/api/v1/faculty/courses/c-cs101", json=full).json()["detail"]
    full["topics"][0]["title"] = "ok"
    full["topics"][0]["subtopics"][0]["questions"][0]["answer_index"] = 9
    assert rao.put("/api/v1/faculty/courses/c-cs101", json=full).status_code == 400


def test_publish_requires_complete_content(as_user):
    rao = as_user(*RAO)
    full = rao.get("/api/v1/faculty/courses/c-cs101").json()
    full["topics"][0]["subtopics"].append({"title": "Bare"})
    rao.put("/api/v1/faculty/courses/c-cs101", json=full)
    r = rao.post("/api/v1/faculty/courses/c-cs101/status", json={"status": "published"})
    assert r.status_code == 400 and "“Bare” has no quiz questions" in r.json()["detail"]
    assert rao.post("/api/v1/faculty/courses/c-cs101/status", json={"status": "draft"}).json() == {
        "id": "c-cs101", "status": "draft"
    }


@pytest.mark.parametrize("path", ["/api/v1/student/catalog", "/api/v1/faculty/courses"])
def test_anonymous_is_401(client, path):
    assert client.get(path).status_code == 401
    assert login(client, "x@y.com", "bad", "student").status_code == 401
