from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token
from app.models import User

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    return value if scheme.lower() == "bearer" and value else None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(ACCESS_COOKIE) or _bearer(request)
    claims = decode_token(token, "access") if token else None
    user = db.get(User, claims["sub"]) if claims else None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in to continue.")
    return user


def require_role(*roles: str) -> Callable[[User], User]:
    """Dependency factory: 401 if not signed in, 403 if the role is not allowed."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this area.")
        return user

    checker.allowed_roles = roles  # type: ignore[attr-defined]  # read by the admin endpoint list
    return checker
