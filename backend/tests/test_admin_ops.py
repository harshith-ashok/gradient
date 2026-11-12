"""Admin dashboard: users, roles and endpoints, logs, issues, system."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import Issue, LogEntry, User
from app.services import monitor, ops

ADMIN = ("richard.hale@gradient.edu", "admin123", "staff")


@pytest.fixture
def admin(as_user):
    return as_user(*ADMIN)


def _crashing(app: FastAPI) -> TestClient:
    def boom():
        raise ValueError("kaboom password=hunter2")

    app.add_api_route("/api/v1/_crash", boom, methods=["GET"])
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------- users
def test_list_filter_and_counts(admin):
    r = admin.get("/api/v1/admin/users").json()
    assert r["by_role"]["admin"] >= 1 and r["total"] == sum(r["by_role"].values())
    only = admin.get("/api/v1/admin/users", params={"role": "faculty"}).json()
    assert only["items"] and all(u["role"] == "faculty" for u in only["items"])
    found = admin.get("/api/v1/admin/users", params={"q": "FATIMA"}).json()
    assert [u["email"] for u in found["items"]] == ["fatima.khan@gradient.edu"]
    assert "password_hash" not in str(r)


def test_create_user_and_sign_in(admin, client):
    body = {"name": "New Teacher", "email": "New.Teacher@Example.edu", "role": "faculty", "password": "longenough1"}
    r = admin.post("/api/v1/admin/users", json=body)
    assert r.status_code == 201 and r.json()["email"] == "new.teacher@example.edu"
    ok = client.post("/api/v1/auth/login", json={"email": "new.teacher@example.edu", "password": "longenough1",
                                                 "portal": "staff"})
    assert ok.status_code == 200
    assert admin.post("/api/v1/admin/users", json=body).status_code == 409
    assert admin.post("/api/v1/admin/users", json={**body, "email": "x@y.edu", "password": "short"}).status_code == 422


def test_change_role_and_deactivate_locks_the_user_out(admin, as_user, db):
    fatima = as_user("fatima.khan@gradient.edu", "student123", "student")
    uid = db.scalar(select(User.id).where(User.email == "fatima.khan@gradient.edu"))
    assert admin.put(f"/api/v1/admin/users/{uid}", json={"is_active": False}).json()["is_active"] is False
    assert fatima.get("/api/v1/auth/me").status_code == 401  # signed out immediately
    back = admin.put(f"/api/v1/admin/users/{uid}", json={"is_active": True, "role": "faculty"})
    assert back.json()["role"] == "faculty"
    assert fatima.get("/api/v1/faculty/courses").status_code == 200


def test_admin_cannot_lock_themselves_out_or_remove_the_last_admin(admin, db):
    me = db.scalar(select(User).where(User.email == ADMIN[0]))
    assert admin.put(f"/api/v1/admin/users/{me.id}", json={"role": "student"}).status_code == 400
    assert admin.put(f"/api/v1/admin/users/{me.id}", json={"is_active": False}).status_code == 400
    other = db.scalar(select(User).where(User.role == "faculty"))
    other.role = "admin"
    db.commit()
    # With two admins the other one may be demoted, but only one active admin may remain
    assert admin.put(f"/api/v1/admin/users/{other.id}", json={"role": "faculty"}).status_code == 200
    assert admin.put("/api/v1/admin/users/nope", json={"name": "x"}).status_code == 404


def test_reset_password(admin, client, db):
    uid = db.scalar(select(User.id).where(User.email == "fatima.khan@gradient.edu"))
    assert admin.post(f"/api/v1/admin/users/{uid}/password", json={"password": "short"}).status_code == 422
    assert admin.post(f"/api/v1/admin/users/{uid}/password", json={"password": "brandnewpass1"}).status_code == 204
    login = lambda pw: client.post("/api/v1/auth/login", json={"email": "fatima.khan@gradient.edu",  # noqa: E731
                                                              "password": pw, "portal": "student"}).status_code
    assert login("student123") == 401 and login("brandnewpass1") == 200


def test_admin_actions_are_audited_without_secrets(admin, db):
    uid = db.scalar(select(User.id).where(User.email == "fatima.khan@gradient.edu"))
    admin.post(f"/api/v1/admin/users/{uid}/password", json={"password": "brandnewpass1"})
    admin.put(f"/api/v1/admin/users/{uid}", json={"role": "faculty"})
    lines = [e.message for e in db.scalars(select(LogEntry).where(LogEntry.logger == "audit"))]
    assert any("reset the password" in m for m in lines) and any("role student→faculty" in m for m in lines)
    assert not any("brandnewpass1" in m for m in lines)


# ---------------------------------------------------------------- roles and endpoints
def test_access_lists_every_route_with_its_real_guard(admin):
    r = admin.get("/api/v1/admin/access").json()
    by = {(e["method"], e["path"]): e for e in r["endpoints"]}
    assert by[("POST", "/api/v1/auth/login")]["access"] == "public"
    assert by[("GET", "/api/v1/auth/me")]["access"] == "signed-in"
    assert by[("GET", "/api/v1/admin/users")]["roles"] == ["admin"]
    assert by[("GET", "/api/v1/student/dashboard")]["roles"] == ["student"]
    assert "admin" in by[("GET", "/api/v1/faculty/courses")]["roles"]
    roles = {x["role"]: x for x in r["roles"]}
    assert set(roles) == {"student", "faculty", "admin"} and roles["admin"]["users"] >= 1
    assert roles["admin"]["endpoints"] > roles["student"]["endpoints"] > 0


def test_access_stats_count_requests_and_errors(admin, as_user, db):
    as_user("fatima.khan@gradient.edu", "student123", "student").get("/api/v1/student/dashboard")
    stats = next(e["stats"] for e in admin.get("/api/v1/admin/access").json()["endpoints"]
                 if e["path"] == "/api/v1/student/dashboard")
    assert stats["requests"] >= 1 and stats["server_errors"] == 0 and stats["last_called"]
    # a denied call is counted as a client error against the same route
    admin.get("/api/v1/student/dashboard")
    again = next(e["stats"] for e in admin.get("/api/v1/admin/access").json()["endpoints"]
                 if e["path"] == "/api/v1/student/dashboard")
    assert again["client_errors"] >= 1


# ---------------------------------------------------------------- logs
def test_requests_are_logged_with_route_template_and_user(admin, db):
    admin.get("/api/v1/admin/users", params={"q": "secret-search-term"})
    row = db.scalars(select(LogEntry).where(LogEntry.path == "/api/v1/admin/users")).first()
    assert row and row.status == 200 and row.role == "admin" and row.user_id and row.request_id
    assert "secret-search-term" not in row.message  # query strings are never stored


def test_log_filters_and_pagination(admin, client):
    client.get("/api/v1/auth/me")  # 401
    admin.get("/api/v1/student/dashboard")  # 403
    bad = admin.get("/api/v1/admin/logs", params={"min_status": 400, "kind": "requests"}).json()
    assert bad["total"] >= 2 and all(i["status"] >= 400 for i in bad["items"])
    warn = admin.get("/api/v1/admin/logs", params={"level": "WARNING"}).json()
    assert all(i["level"] != "INFO" for i in warn["items"])
    one = admin.get("/api/v1/admin/logs", params={"page_size": 1}).json()
    assert len(one["items"]) == 1 and one["total"] > 1
    by_id = admin.get("/api/v1/admin/logs", params={"request_id": bad["items"][0]["request_id"]}).json()
    assert by_id["total"] >= 1
    named = [i for i in admin.get("/api/v1/admin/logs", params={"path": "/admin/users"}).json()["items"]]
    assert all("admin/users" in i["path"] for i in named)


def test_log_viewer_does_not_log_itself(admin, db):
    admin.get("/api/v1/admin/logs")
    assert not db.scalars(select(LogEntry).where(LogEntry.path == "/api/v1/admin/logs")).first()


def test_health_checks_are_not_logged(client, db):
    client.get("/api/health")
    assert not db.scalars(select(LogEntry).where(LogEntry.path.like("/api/health%"))).first()


def test_old_logs_are_pruned(db):
    from datetime import timedelta

    from app.models.base import utcnow

    db.add(LogEntry(level="INFO", logger="x", message="old", ts=utcnow() - timedelta(days=60)))
    db.add(LogEntry(level="INFO", logger="x", message="new"))
    db.commit()
    assert monitor.prune(db) == 1
    assert [e.message for e in db.scalars(select(LogEntry))] == ["new"]


# ---------------------------------------------------------------- issues
def test_unhandled_error_becomes_an_issue_with_stack_trace(app, as_user, db):
    c = _crashing(app)
    r = c.get("/api/v1/_crash")
    assert r.status_code == 500 and r.json()["request_id"] == r.headers["X-Request-ID"]
    assert "kaboom" not in r.text  # callers never see internals
    issue = db.scalars(select(Issue)).one()
    assert issue.exc_type == "ValueError" and issue.status == "open" and issue.count == 1
    assert "hunter2" not in issue.title  # secrets are masked
    assert "_crash" in issue.culprit or "boom" in issue.culprit
    crash_log = db.scalars(select(LogEntry).where(LogEntry.status == 500)).one()
    assert crash_log.level == "ERROR" and crash_log.request_id == r.headers["X-Request-ID"]


def test_same_bug_groups_and_resolved_issue_reopens(app, admin, db):
    c = _crashing(app)
    for _ in range(3):
        c.get("/api/v1/_crash")
    listing = admin.get("/api/v1/admin/issues").json()
    assert listing["total"] == 1 and listing["items"][0]["count"] == 3 and listing["by_status"]["open"] == 1
    iid = listing["items"][0]["id"]
    detail = admin.get(f"/api/v1/admin/issues/{iid}").json()
    assert len(detail["events"]) == 3 and "Traceback" in detail["events"][0]["stack_trace"]
    assert "hunter2" not in detail["events"][0]["stack_trace"] + detail["events"][0]["message"]
    done = admin.put(f"/api/v1/admin/issues/{iid}", json={"status": "resolved", "note": "fixed in v2"}).json()
    assert done["status"] == "resolved" and done["note"] == "fixed in v2"
    assert admin.get("/api/v1/admin/issues", params={"status": "open"}).json()["total"] == 0
    c.get("/api/v1/_crash")
    assert admin.get(f"/api/v1/admin/issues/{iid}").json()["status"] == "open"  # it came back
    assert admin.get("/api/v1/admin/issues/missing").status_code == 404


def test_logged_exceptions_become_issues_once(app, db):
    import logging

    log = logging.getLogger("worker")
    try:
        raise RuntimeError("job exploded")
    except RuntimeError:
        log.exception("job crashed")
    issue = db.scalars(select(Issue)).one()
    assert issue.title.startswith("RuntimeError") and issue.count == 1
    assert db.scalars(select(LogEntry).where(LogEntry.logger == "worker")).one().level == "ERROR"


def test_secrets_are_masked():
    text = monitor.scrub("auth $argon2id$v=19$m=65536$abc$def and eyJhbGciOi.eyJzdWIiOi.sig with token=abc123")
    assert "argon2" not in text and "eyJ" not in text and "abc123" not in text


def test_monitoring_failure_never_breaks_a_request(app, monkeypatch, client):
    from contextlib import contextmanager

    @contextmanager
    def broken():
        raise RuntimeError("log database down")
        yield  # pragma: no cover

    monkeypatch.setattr(monitor, "open_session", broken)
    assert client.get("/api/v1/auth/demo-logins").status_code in (200, 404)


# ---------------------------------------------------------------- system
def test_system_overview(admin, db):
    admin.get("/api/v1/student/dashboard")
    s = admin.get("/api/v1/admin/system").json()
    assert s["checks"]["postgres"] == "ok" and len(s["traffic"]) == 24
    assert s["requests_24h"] >= 1 and s["client_errors_24h"] >= 1
    assert set(s["jobs"]) == {"queued", "running", "succeeded", "failed"}
    assert "jwt_secret" not in str(s).lower()


def test_ops_service_registry_matches_openapi(app):
    paths = {(m.upper(), p) for p, ops_ in app.openapi()["paths"].items() for m in ops_ if p.startswith("/api")}
    listed = {(e["method"], e["path"]) for e in ops.endpoint_registry(app.state.routers)}
    assert paths == listed
