"""Create (or reset the password of) an account. Used to make the first admin in production,
where the demo seed does not run.

    uv run python -m scripts.create_user "Ada Lovelace" ada@example.edu admin
    # password from $NEW_USER_PASSWORD, or prompted
"""

import getpass
import os
import re
import sys
import uuid

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import session_factory
from app.core.security import hash_password
from app.models import User

ROLES = ("student", "faculty", "admin")

if len(sys.argv) != 4 or sys.argv[3] not in ROLES:
    sys.exit(f"usage: create_user NAME EMAIL {{{'|'.join(ROLES)}}}")
name, email, role = sys.argv[1], sys.argv[2].strip().lower(), sys.argv[3]
if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
    sys.exit("That does not look like an email address.")
password = os.environ.get("NEW_USER_PASSWORD") or getpass.getpass("Password: ")
if get_settings().env != "dev" and len(password) < 12:
    sys.exit("Use a password of at least 12 characters.")

with session_factory()() as db:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        user.password_hash, user.role, user.name, user.is_active = hash_password(password), role, name, True
        action = "updated"
    else:
        db.add(User(id=f"u-{uuid.uuid4().hex[:10]}", name=name, email=email, role=role,
                    password_hash=hash_password(password), is_active=True))
        action = "created"
    db.commit()
print(f"{action} {role} {email}")
