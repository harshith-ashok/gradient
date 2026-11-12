"""Dev/test helper: delete accounts whose email starts with a prefix (and their data).

    uv run python -m scripts.delete_users e2e-
"""

import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import session_factory
from app.models import User

if get_settings().env != "dev":
    sys.exit("Refusing to run outside ENV=dev")
if len(sys.argv) != 2 or len(sys.argv[1]) < 3:
    sys.exit("usage: delete_users EMAIL_PREFIX (at least 3 characters)")

with session_factory()() as db:
    gone = db.scalars(select(User).where(User.email.startswith(sys.argv[1]))).all()
    for u in gone:
        db.delete(u)
    db.commit()
print(f"deleted {len(gone)} user(s)")
