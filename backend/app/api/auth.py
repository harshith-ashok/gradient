import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core import ratelimit
from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import ACCESS_COOKIE, REFRESH_COOKIE, get_current_user
from app.core.security import create_token, decode_token
from app.models import User
from app.schemas.auth import DemoLogin, LoginRequest, Message, UserOut
from app.services.auth import AuthError, authenticate


def client_ip(request: Request) -> str:
    if get_settings().trust_forwarded_for:
        fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if fwd:
            return fwd
    return request.client.host if request.client else "unknown"


router = APIRouter(prefix="/auth", tags=["auth"])

DEMO_LOGINS = Path(__file__).parent.parent / "seed" / "fixtures" / "demo_logins.json"


def _set_cookies(response: Response, user: User) -> None:
    s = get_settings()
    common = {
        "httponly": True,
        "secure": s.cookie_secure,
        "samesite": "lax",
        "domain": s.cookie_domain,
        "path": "/",
    }
    response.set_cookie(
        ACCESS_COOKIE, create_token(user.id, user.role, "access"),
        max_age=s.access_ttl_minutes * 60, **common,
    )
    response.set_cookie(
        REFRESH_COOKIE, create_token(user.id, user.role, "refresh"),
        max_age=s.refresh_ttl_days * 86400, **common,
    )


LOGIN_ERRORS = {401: {"model": Message}, 403: {"model": Message}, 429: {"model": Message}}


@router.post("/login", response_model=UserOut, responses=LOGIN_ERRORS)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> User:
    ip = client_ip(request)
    wait = ratelimit.blocked(body.email, ip)
    if wait:
        raise HTTPException(429, f"Too many failed attempts. Try again in {-(-wait // 60)} minutes.",
                            headers={"Retry-After": str(wait)})
    try:
        user = authenticate(db, body.email, body.password, body.portal)
    except AuthError as e:
        if e.status_code == 401:  # a wrong password or unknown account; a portal mismatch is not guessing
            ratelimit.record_failure(body.email, ip)
        raise HTTPException(e.status_code, e.message) from e
    ratelimit.clear(body.email, ip)
    _set_cookies(response, user)
    return user


@router.post("/refresh", response_model=UserOut, responses={401: {"model": Message}})
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(REFRESH_COOKIE)
    claims = decode_token(token, "refresh") if token else None
    user = db.get(User, claims["sub"]) if claims else None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired. Please sign in again.")
    _set_cookies(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    s = get_settings()
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, path="/", domain=s.cookie_domain)


@router.get("/me", response_model=UserOut, responses={401: {"model": Message}})
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/demo-logins", response_model=list[DemoLogin])
def demo_logins() -> list[dict]:
    """Quick-fill accounts for the login page. Only served when DEMO_MODE is on."""
    if not get_settings().demo_mode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return json.loads(DEMO_LOGINS.read_text())
