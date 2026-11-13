"""Coding challenges: authoring, submitting, judging (local backend), and access rules."""

import shutil

import pytest
from fastapi.testclient import TestClient

from app.models import CodeSubmission, CodingProblem
from app.services import judge
from app.services.courses import CourseError

FACULTY = ("ananya.rao@gradient.edu", "faculty123", "staff")
STUDENT = ("fatima.khan@gradient.edu", "student123", "student")
HAS_GCC = shutil.which("gcc") is not None

DOUBLE = "n = int(input())\nprint(n * 2)\n"
TESTS = [
    {"input": "3\n", "expected": "6\n", "sample": True},
    {"input": "10\n", "expected": "20\n", "sample": False},
    {"input": "7\n", "expected": "14\n", "sample": False},
]


@pytest.fixture(autouse=True)
def local_judge():
    judge.set_backend(judge.LocalBackend())
    yield
    judge.set_backend(None)


@pytest.fixture
def fac(as_user):
    return as_user(*FACULTY)


@pytest.fixture
def stu(as_user):
    return as_user(*STUDENT)


@pytest.fixture
def subtopic_id(fac):
    return fac.get("/api/v1/faculty/courses/c-cs101").json()["topics"][0]["subtopics"][0]["id"]


def body(**over):
    base = {"title": "Double it", "statement": "Read `n`, print `2n`.", "level": "beginner",
            "languages": ["python", "c"], "starter": {"python": "# your code\n"}, "time_limit_ms": 1000,
            "memory_mb": 128, "tests": TESTS}
    return {**base, **over}


@pytest.fixture
def problem(fac, subtopic_id):
    r = fac.post(f"/api/v1/faculty/subtopics/{subtopic_id}/problems", json=body())
    assert r.status_code == 201, r.text
    return r.json()


def run_code(client, db, pid, code, language="python", mode="run"):
    r = client.post(f"/api/v1/student/problems/{pid}/submit", json={"language": language, "code": code, "mode": mode})
    assert r.status_code == 202, r.text
    judge.process_pending(db)
    return client.get(f"/api/v1/student/submissions/{r.json()['id']}").json()


# ---------------------------------------------------------------- authoring
def test_faculty_creates_edits_and_deletes_a_problem(fac, subtopic_id, problem):
    listed = fac.get(f"/api/v1/faculty/subtopics/{subtopic_id}/problems").json()
    assert [p["title"] for p in listed] == ["Double it"] and len(listed[0]["tests"]) == 3
    edited = fac.put(f"/api/v1/faculty/problems/{problem['id']}", json=body(title="Twice")).json()
    assert edited["title"] == "Twice" and edited["starter"] == {"python": "# your code\n"}
    assert fac.delete(f"/api/v1/faculty/problems/{problem['id']}").status_code == 204
    assert fac.get(f"/api/v1/faculty/subtopics/{subtopic_id}/problems").json() == []


@pytest.mark.parametrize("bad", [
    {"tests": []},
    {"tests": [{"input": "1", "expected": "1", "sample": False}]},  # no sample to show
    {"languages": []},
    {"languages": ["cobol"]},
    {"time_limit_ms": 60_000},
    {"statement": "   "},
    {"title": ""},
])
def test_invalid_problems_are_refused(fac, subtopic_id, bad):
    assert fac.post(f"/api/v1/faculty/subtopics/{subtopic_id}/problems", json=body(**bad)).status_code in (400, 422)


def test_only_the_owner_edits_problems(fac, as_user, problem, subtopic_id):
    other = as_user("marcus.lee@gradient.edu", "faculty123", "staff")
    assert other.get(f"/api/v1/faculty/subtopics/{subtopic_id}/problems").status_code == 403
    assert other.put(f"/api/v1/faculty/problems/{problem['id']}", json=body()).status_code == 403
    assert other.delete(f"/api/v1/faculty/problems/{problem['id']}").status_code == 403
    assert other.post(f"/api/v1/faculty/problems/{problem['id']}/test-run",
                      json={"language": "python", "code": DOUBLE}).status_code == 403


# ---------------------------------------------------------------- what students see
def test_students_never_receive_hidden_tests(stu, problem, subtopic_id):
    d = stu.get(f"/api/v1/student/problems/{problem['id']}").json()
    assert d["samples"] == [{"input": "3\n", "expected": "6\n"}]
    assert d["hidden_tests"] == 2
    text = stu.get(f"/api/v1/student/problems/{problem['id']}").text
    assert "20\\n" not in text and "14\\n" not in text and '"tests"' not in text  # hidden data is not in the payload
    brief = stu.get(f"/api/v1/student/subtopics/{subtopic_id}/problems").json()
    assert brief == [{"id": problem["id"], "title": "Double it", "level": "beginner",
                      "languages": ["python", "c"], "solved": False, "attempts": 0}]


def test_unpublished_courses_hide_their_problems(fac, stu, db, problem):
    from app.models import Course

    db.get(Course, "c-cs101").status = "draft"
    db.commit()
    assert stu.get(f"/api/v1/student/problems/{problem['id']}").status_code == 404
    assert stu.post(f"/api/v1/student/problems/{problem['id']}/submit",
                    json={"language": "python", "code": DOUBLE}).status_code == 404


# ---------------------------------------------------------------- judging
def test_run_checks_only_samples_and_submit_checks_everything(stu, db, problem):
    r = run_code(stu, db, problem["id"], DOUBLE)
    assert r["state"] == "done" and r["verdict"] == "accepted" and (r["passed"], r["total"]) == (1, 1)
    s = run_code(stu, db, problem["id"], DOUBLE, mode="submit")
    assert s["verdict"] == "accepted" and (s["passed"], s["total"]) == (3, 3) and s["runtime_ms"] is not None
    brief = stu.get(f"/api/v1/student/subtopics/{problem['subtopic_id']}/problems").json()[0]
    assert brief["solved"] is True and brief["attempts"] == 1  # only graded submits count


def test_wrong_answer_keeps_hidden_data_hidden(stu, db, problem):
    cheat = "n = int(input())\nprint(6 if n == 3 else 0)\n"  # right on the sample, wrong elsewhere
    s = run_code(stu, db, problem["id"], cheat, mode="submit")
    assert s["verdict"] == "wrong_answer" and (s["passed"], s["total"]) == (1, 3)
    hidden = [t for t in s["results"] if not t["sample"]]
    assert len(hidden) == 2 and all(t["verdict"] == "wrong_answer" for t in hidden)
    for t in hidden:  # a student learns that it failed, never what the test was
        assert t["input"] is None and t["expected"] is None and t["stdout"] is None and t["stderr"] is None
    sample = next(t for t in s["results"] if t["sample"])
    assert sample["input"] == "3\n" and sample["stdout"] == "6\n"
    assert "20\\n" not in str(s["results"]) and "14\\n" not in str(s["results"])


def test_runtime_error_and_traceback(stu, db, problem):
    s = run_code(stu, db, problem["id"], "raise ValueError('boom')\n")
    assert s["verdict"] == "runtime_error" and "ValueError" in s["results"][0]["stderr"]


def test_infinite_loop_is_stopped(stu, db, problem, fac):
    fac.put(f"/api/v1/faculty/problems/{problem['id']}", json=body(time_limit_ms=300))
    s = run_code(stu, db, problem["id"], "while True:\n    pass\n", mode="submit")
    assert s["verdict"] == "time_limit" and s["passed"] == 0
    assert [t["verdict"] for t in s["results"]] == ["time_limit", "skipped", "skipped"]  # no point waiting 3 times


def test_output_flood_is_cut_off(stu, db, problem):
    s = run_code(stu, db, problem["id"], "while True:\n    print('x' * 1000)\n", mode="run")
    assert s["verdict"] in ("output_limit", "runtime_error", "time_limit")
    assert len(str(s["results"])) < 20_000


@pytest.mark.skipif(not HAS_GCC, reason="no C compiler on this machine")
def test_c_compiles_runs_and_reports_compile_errors(stu, db, problem):
    ok = '#include <stdio.h>\nint main(void){int n; scanf("%d", &n); printf("%d\\n", n * 2); return 0;}\n'
    assert run_code(stu, db, problem["id"], ok, "c", "submit")["verdict"] == "accepted"
    bad = run_code(stu, db, problem["id"], "int main( { return 0 }\n", "c")
    assert bad["verdict"] == "compile_error" and bad["compile_output"] and bad["results"] == []


def test_crash_and_missing_sandbox_become_clear_verdicts(stu, db, problem):
    class Down:
        def run(self, payload, timeout):
            raise judge.JudgeUnavailable("no docker")

    judge.set_backend(Down())
    s = run_code(stu, db, problem["id"], DOUBLE)
    assert s["verdict"] == "internal_error" and "unavailable" in s["message"]
    assert "docker" not in s["message"].lower()  # internals stay in the logs


# ---------------------------------------------------------------- access and limits
def test_students_only_see_their_own_submissions(stu, as_user, db, problem):
    mine = run_code(stu, db, problem["id"], DOUBLE)
    other = as_user("daniel.okafor@gradient.edu", "student123", "student")
    assert other.get(f"/api/v1/student/submissions/{mine['id']}").status_code == 404
    assert [h["id"] for h in stu.get(f"/api/v1/student/problems/{problem['id']}/submissions").json()] == [mine["id"]]
    assert other.get(f"/api/v1/student/problems/{problem['id']}/submissions").json() == []


def test_one_run_at_a_time_and_a_per_minute_cap(stu, db, problem, monkeypatch):
    post = lambda: stu.post(f"/api/v1/student/problems/{problem['id']}/submit",  # noqa: E731
                            json={"language": "python", "code": DOUBLE})
    assert post().status_code == 202
    assert post().status_code == 429  # the first is still queued
    judge.process_pending(db)
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "submissions_per_minute", 2)
    assert post().status_code == 202  # second of the minute
    judge.process_pending(db)
    assert post().status_code == 429


def test_code_size_and_language_limits(stu, problem, monkeypatch):
    from app.core.config import get_settings

    url = f"/api/v1/student/problems/{problem['id']}/submit"
    assert stu.post(url, json={"language": "cpp", "code": "x"}).status_code == 400  # not allowed for this problem
    assert stu.post(url, json={"language": "ruby", "code": "x"}).status_code == 422
    assert stu.post(url, json={"language": "python", "code": ""}).status_code == 422
    monkeypatch.setattr(get_settings(), "max_code_bytes", 10)
    assert stu.post(url, json={"language": "python", "code": "x" * 11}).status_code == 413


def test_faculty_test_run_shows_everything(fac, db, problem):
    r = fac.post(f"/api/v1/faculty/problems/{problem['id']}/test-run", json={"language": "python", "code": DOUBLE})
    assert r.status_code == 202
    judge.process_pending(db)
    s = fac.get(f"/api/v1/faculty/submissions/{r.json()['id']}").json()
    assert s["mode"] == "check" and s["verdict"] == "accepted" and s["total"] == 3
    assert all(t["input"] is not None and t["expected"] is not None for t in s["results"])  # staff see hidden tests


def test_deleting_a_problem_removes_its_submissions(fac, stu, db, problem):
    run_code(stu, db, problem["id"], DOUBLE)
    fac.delete(f"/api/v1/faculty/problems/{problem['id']}")
    db.expire_all()
    assert db.query(CodeSubmission).count() == 0 and db.query(CodingProblem).count() == 0


def test_a_dead_judge_does_not_leave_runs_hanging(stu, db, problem):
    from datetime import timedelta

    r = stu.post(f"/api/v1/student/problems/{problem['id']}/submit", json={"language": "python", "code": DOUBLE})
    sub = db.get(CodeSubmission, r.json()["id"])
    sub.state, sub.started_at = "running", judge.clock.now() - timedelta(minutes=30)
    db.commit()
    assert judge.fail_stale(db) == 1
    got = stu.get(f"/api/v1/student/submissions/{r.json()['id']}").json()
    assert got["state"] == "done" and got["verdict"] == "internal_error"


def test_local_judge_refuses_to_run_outside_dev(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "env", "prod")
    with pytest.raises(judge.JudgeUnavailable):
        judge.LocalBackend()


def test_unknown_things_are_404(stu, fac):
    assert stu.get("/api/v1/student/problems/nope").status_code == 404
    assert stu.get("/api/v1/student/submissions/nope").status_code == 404
    assert fac.get("/api/v1/faculty/subtopics/nope/problems").status_code == 404
    assert isinstance(CourseError("x"), Exception) and isinstance(stu, TestClient)
