"""Demo student history: students who enrolled days ago, sat the pre-test, worked through their
plans, and (in a few cases) failed a quiz so the adaptive logic has already fired.

It drives the real learning service with the clock moved back, so the seeded data is exactly what
the app would have produced (ported from the prototype's seed.js).
"""

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.models import Enrollment, Setting, User
from app.services import learning

MARKER = "seed_history_v1"

# (user, course, days ago, pre-test accuracy, accuracies of the quizzes taken in order, tasks today)
SCENARIOS = [
    ("u-meera", "c-cs101", 3, 0.5, [1, 0.25, 1, 0.75, 1], 1),
    ("u-daniel", "c-cs101", 6, 0.8, [1, 1, 1, 1, 0.75], 1),
    ("u-daniel", "cpp-cs201", 2, 0.5, [1, 0.75], 0),
    ("u-sofia", "c-cs101", 5, 0.2, [0.5, 0.25, 0.5, 1, 0.25], 1),
    ("u-kenji", "econ-101", 3, 0.6, [1, 1, 0.75], 1),
    ("u-priya", "cpp-cs201", 4, 0.3, [0.75, 1, 0.5], 0),
    ("u-lucas", "econ-101", 2, 0.4, [0.75], 1),
    ("u-lucas", "c-cs101", 1, 0.5, [], 0),
]


def _answers(db: Session, quiz: dict, acc: float) -> dict[str, int]:
    key = learning.answer_key(db, quiz["quiz_id"])
    out = {}
    for i, q in enumerate(quiz["questions"]):
        right = ((i * 7 + 3) % 10) / 10 < acc  # deterministic: the same accuracy gives the same result
        out[q["id"]] = key[q["id"]] if right else (key[q["id"]] + 1) % len(q["options"])
    return out


def _sit(db: Session, user: User, course_id: str, acc: float, **req) -> None:
    quiz = learning.start_quiz(db, user, course_id, **req)
    learning.submit_quiz(db, user, quiz["quiz_id"], _answers(db, quiz, acc))


def _simulate(db: Session, user_id: str, course_id: str, days_ago: int, pre: float, quiz_acc: list[float],
              today_tasks: int) -> None:
    user = db.get(User, user_id)
    queue = list(quiz_acc)
    next_acc = lambda: queue.pop(0) if queue else 0.9  # noqa: E731
    clock.set_days_ago(days_ago)
    _sit(db, user, course_id, pre, kind="pretest")
    for d in range(days_ago + 1):
        clock.set_days_ago(days_ago - d)
        today = clock.today()
        budget = today_tasks if d == days_ago else float("inf")
        for _ in range(40):
            if budget <= 0:
                break
            enr = learning.get_enrollment(db, user, course_id)
            t = next((x for x in enr.tasks if x.status != "done" and x.scheduled_for <= today), None)
            if t is None:
                break
            if t.type in ("study", "remediation"):
                learning.complete_task(db, user, course_id, t.id)
            elif t.type == "topic_quiz":
                _sit(db, user, course_id, next_acc(), kind="topic", topic_id=t.topic_id)
            else:
                _sit(db, user, course_id, next_acc(), kind="subtopic", subtopic_id=t.subtopic_id)
            budget -= 1


def seed_history(db: Session) -> int:
    if db.get(Setting, MARKER) or db.scalar(select(Enrollment.id).limit(1)):
        return 0  # already seeded, or real students exist: never mix demo history into real data
    rng_state = learning.rng
    learning.rng = random.Random(7)  # repeatable question picks
    try:
        for s in SCENARIOS:
            _simulate(db, *s)
    finally:
        clock.reset()
        learning.rng = rng_state
    db.add(Setting(key=MARKER, value=True))
    db.commit()
    return len(SCENARIOS)
