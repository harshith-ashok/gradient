"""Dev/test helper: remove a student's enrolments (plan, mastery, attempts) so flows can be re-run.

    uv run python -m scripts.reset_student u-fatima
"""

import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import session_factory
from app.models import Enrollment, QuizSession

if get_settings().env != "dev":
    sys.exit("Refusing to run outside ENV=dev")

user_id = sys.argv[1]
with session_factory()() as db:
    for e in db.scalars(select(Enrollment).where(Enrollment.user_id == user_id)):
        db.delete(e)  # plan tasks, mastery, notices, attempts cascade
    for s in db.scalars(select(QuizSession).where(QuizSession.user_id == user_id)):
        db.delete(s)
    db.commit()
print(f"reset {user_id}")
