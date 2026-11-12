import jwt
import pytest

from app.core.config import get_settings
from app.core.security import create_token
from tests.conftest import login

STUDENT = ("meera.iyer@gradient.edu", "student123", "student")
FACULTY = ("ananya.rao@gradient.edu", "faculty123", "staff")
ADMIN = ("richard.hale@gradient.edu", "admin123", "staff")


@pytest.mark.parametrize(("account", "role"), [(STUDENT, "student"), (FACULTY, "faculty"), (ADMIN, "admin")])
def test_demo_accounts_log_in_with_their_role(client, account, role):
    r = login(client, *account)
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == role
    assert "password" not in body and "password_hash" not in body
    assert client.get("/api/v1/auth/me").json()["email"] == account[0]


def test_cookies_are_httponly(client):
    r = login(client, *STUDENT)
    cookies = r.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert all("HttpOnly" in c and "SameSite=lax" in c for c in cookies)


def test_email_is_case_insensitive(client):
    assert login(client, "MEERA.IYER@gradient.edu", "student123", "student").status_code == 200


def test_wrong_password_and_unknown_email_look_the_same(client):
    a = login(client, "meera.iyer@gradient.edu", "nope", "student")
    b = login(client, "nobody@gradient.edu", "nope", "student")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_portal_mismatch_is_403(client):
    assert login(client, STUDENT[0], STUDENT[1], "staff").status_code == 403
    assert login(client, FACULTY[0], FACULTY[1], "student").status_code == 403
    # No session is created on a mismatch
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_requires_login(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_logout_clears_session(client):
    login(client, *STUDENT)
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_refresh_issues_new_access_token(client):
    login(client, *STUDENT)
    client.cookies.delete("access_token")
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/refresh").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200


def test_access_token_cannot_be_used_as_refresh(client):
    login(client, *STUDENT)
    client.cookies.set("refresh_token", client.cookies.get("access_token"))
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_refresh_token_cannot_be_used_as_access(client):
    login(client, *STUDENT)
    client.cookies.set("access_token", client.cookies.get("refresh_token"))
    assert client.get("/api/v1/auth/me").status_code == 401


def test_tampered_and_expired_tokens_rejected(client):
    s = get_settings()
    forged = jwt.encode(
        {"sub": "u-hale", "role": "admin", "typ": "access"}, "wrong-secret", algorithm=s.jwt_algorithm
    )
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    expired = jwt.encode(
        {"sub": "u-hale", "role": "admin", "typ": "access", "exp": 1}, s.jwt_secret, algorithm=s.jwt_algorithm
    )
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_role_is_read_from_database_not_token(client):
    """A token claiming admin for a student account must not grant admin access."""
    token = create_token("u-meera", "admin", "access")
    r = client.get("/_test/admin", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


@pytest.mark.parametrize(
    ("account", "allowed"),
    [(STUDENT, "student"), (FACULTY, "faculty"), (ADMIN, "admin")],
)
def test_rbac_matrix(as_user, account, allowed):
    c = as_user(*account)
    for role in ("student", "faculty", "admin"):
        assert c.get(f"/_test/{role}").status_code == (200 if role == allowed else 403)


def test_rbac_anonymous_is_401(client):
    assert client.get("/_test/student").status_code == 401


def test_demo_logins_listing_and_demo_mode_off(client, monkeypatch):
    assert len(client.get("/api/v1/auth/demo-logins").json()) == 4
    monkeypatch.setattr(get_settings(), "demo_mode", False)
    assert client.get("/api/v1/auth/demo-logins").status_code == 404
