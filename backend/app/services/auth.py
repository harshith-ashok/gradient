from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User

# Verifying against this when the email is unknown keeps response time similar,
# so login timing does not reveal which emails exist.
_DUMMY_HASH = hash_password("not-a-real-password")


class AuthError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def authenticate(db: Session, email: str, password: str, portal: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok or not user.is_active:
        raise AuthError("Incorrect email or password.", 401)
    is_staff = user.role in ("faculty", "admin")
    if portal == "student" and is_staff:
        raise AuthError("This account belongs to the Faculty / Management portal.", 403)
    if portal == "staff" and not is_staff:
        raise AuthError("This account belongs to the Student portal.", 403)
    return user
