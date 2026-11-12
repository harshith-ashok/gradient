"""Security and operations: login throttling, headers, request ids, role audit, model-call tracing."""

import json
import logging

import pytest

from app.core.config import get_settings
from app.main import app

BAD = {"email": "fatima.khan@gradient.edu", "password": "wrong-password", "portal": "student"}
GOOD = {"email": "fatima.khan@gradient.edu", "password": "student123", "portal": "student"}


def login(c, body):
    return c.post("/api/v1/auth/login", json=body)


# ------------------------------------------------------------ login throttling


def test_repeated_wrong_passwords_are_throttled_then_the_right_one_is_refused_too(client):
    limit = get_settings().login_max_failures
    for _ in range(limit):
        assert login(client, BAD).status_code == 401
    r = login(client, BAD)
    assert r.status_code == 429 and "Retry-After" in r.headers
    assert login(client, GOOD).status_code == 429  # an attacker who guesses right still waits


def test_a_successful_login_resets_the_count(client):
    for _ in range(get_settings().login_max_failures - 1):
        login(client, BAD)
    assert login(client, GOOD).status_code == 200
    for _ in range(get_settings().login_max_failures - 1):
        assert login(client, BAD).status_code == 401  # the counter started again


def test_one_accounts_failures_do_not_lock_another_account(client):
    for _ in range(get_settings().login_max_failures):
        login(client, BAD)
    other = {"email": "meera.iyer@gradient.edu", "password": "student123", "portal": "student"}
    assert login(client, other).status_code == 200


def test_a_portal_mismatch_is_not_counted_as_guessing(client):
    wrong_portal = {**GOOD, "portal": "staff"}
    for _ in range(get_settings().login_max_failures + 2):
        assert login(client, wrong_portal).status_code == 403
    assert login(client, GOOD).status_code == 200


def test_the_forwarded_address_is_only_trusted_when_configured(client, monkeypatch):
    s = get_settings()
    for i in range(s.login_max_failures):
        client.post("/api/v1/auth/login", json=BAD, headers={"X-Forwarded-For": f"10.0.0.{i}"})
    # ignored by default, so the same caller was counted and is now blocked
    assert login(client, BAD).status_code == 429
    monkeypatch.setattr(s, "trust_forwarded_for", True)
    assert client.post("/api/v1/auth/login", json=BAD, headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 401


def test_login_still_works_when_redis_is_down(client, fake_cache, monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("redis down")

    for name in ("get", "incr", "expire", "ttl"):
        monkeypatch.setattr(fake_cache, name, boom)
    assert login(client, GOOD).status_code == 200
    assert login(client, BAD).status_code == 401


# ------------------------------------------------------ headers and request ids


def test_security_headers_and_request_id(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff" and r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Cache-Control"] == "no-store" and len(r.headers["X-Request-ID"]) >= 8
    kept = client.get("/api/health", headers={"X-Request-ID": "trace-12345678"})
    assert kept.headers["X-Request-ID"] == "trace-12345678"
    # an id with odd characters is replaced, never echoed into logs or headers
    odd = client.get("/api/health", headers={"X-Request-ID": "bad id\t<script>"})
    assert odd.headers["X-Request-ID"] != "bad id\t<script>"


def test_requests_are_logged_with_their_id(client, caplog):
    with caplog.at_level(logging.INFO, logger="gradient.access"):
        r = client.get("/api/health")
    rec = next(x for x in caplog.records if x.name == "gradient.access")
    assert rec.http_status == 200 and rec.duration_ms >= 0 and "/api/health" in rec.getMessage()
    assert r.headers["X-Request-ID"]


def test_json_log_format():
    from app.core.observability import JsonFormatter

    rec = logging.LogRecord("x", logging.INFO, __file__, 1, "hello %s", ("there",), None)
    out = json.loads(JsonFormatter().format(rec))
    assert out["msg"] == "hello there" and out["level"] == "INFO" and "request_id" in out


def test_cors_allows_only_the_configured_origin(client):
    def preflight(origin):
        return client.options("/api/v1/auth/me",
                              headers={"Origin": origin, "Access-Control-Request-Method": "GET"})

    ok = preflight("http://localhost:3000")
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = preflight("https://evil.example")
    assert "access-control-allow-origin" not in bad.headers


# ------------------------------------------------------------------ role audit

PUBLIC = {"/api/health", "/api/health/ready", "/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/logout",
          "/api/v1/auth/demo-logins"}


def api_routes():
    for path, ops in app.openapi()["paths"].items():
        if path.startswith("/api") and path not in PUBLIC:
            for method in ops:
                yield method.upper(), path


def call(c, method, path):
    url = path.replace("{", "").replace("}", "")  # path params become plain strings
    kwargs = {"json": {}} if method in ("POST", "PUT") else {}
    return c.request(method, url, **kwargs)


def test_every_non_public_route_requires_a_session(client):
    routes = list(api_routes())
    assert len(routes) > 20
    open_ = [(m, p) for m, p in routes if call(client, m, p).status_code != 401]
    assert open_ == [], f"reachable without signing in: {open_}"


@pytest.mark.parametrize(("account", "forbidden"), [
    (("fatima.khan@gradient.edu", "student123", "student"), ("/api/v1/faculty", "/api/v1/admin", "/api/v1/jobs")),
    (("ananya.rao@gradient.edu", "faculty123", "staff"), ("/api/v1/student", "/api/v1/admin")),
])
def test_roles_cannot_reach_other_roles_routes(as_user, account, forbidden):
    c = as_user(*account)
    leaks = [(m, p) for m, p in api_routes() if p.startswith(forbidden) and call(c, m, p).status_code != 403]
    assert leaks == [], f"wrong role got through: {leaks}"


def test_admin_cannot_reach_student_routes(as_user):
    c = as_user("richard.hale@gradient.edu", "admin123", "staff")
    leaks = [(m, p) for m, p in api_routes() if p.startswith("/api/v1/student") and call(c, m, p).status_code != 403]
    assert leaks == []


# -------------------------------------------------------------- model tracing


def test_every_model_call_is_traced(fake_ai, caplog):
    from app.agents.schemas import TopicList

    with caplog.at_level(logging.INFO, logger="app.agents.llm"):
        fake_ai.structured("sys", "<syllabus>\n1. Intro to databases\n</syllabus>", TopicList)
    rec = next(r for r in caplog.records if hasattr(r, "llm"))
    assert rec.llm["schema"] == "TopicList" and rec.llm["outcome"] == "ok" and rec.llm["ms"] >= 0


def test_invalid_and_unreachable_model_calls_are_traced_as_failures(fake_ai, caplog):
    from app.agents.llm import LLMError
    from app.agents.schemas import TopicList

    fake_ai.responder = lambda m, s: "not json"
    with caplog.at_level(logging.INFO, logger="app.agents.llm"), pytest.raises(LLMError):
        fake_ai.structured("sys", "x", TopicList)
    assert [r.llm["outcome"] for r in caplog.records if hasattr(r, "llm")] == ["invalid", "invalid"]
