"""Dev/test helper: delete courses whose code starts with a prefix (and their uploads).

    uv run python -m scripts.delete_courses E2E
"""

import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import session_factory
from app.models import Course

if get_settings().env != "dev":
    sys.exit("Refusing to run outside ENV=dev")

prefix = sys.argv[1]
with session_factory()() as db:
    gone = db.scalars(select(Course).where(Course.code.startswith(prefix))).all()
    for c in gone:
        db.delete(c)
    db.commit()
print(f"deleted {len(gone)} course(s)")
