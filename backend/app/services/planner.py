"""Pure scheduling logic for study plans (ported from the prototype's planner.js).

No database access in here, so the rules are easy to test. `learning.py` loads rows into these
dataclasses, applies the rules, and writes the result back.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from math import floor

from app.models.base import new_id

# Minutes per task type.
MINUTES = {"study": 25, "confirm": 15, "quiz": 15, "remediation": 20, "retake": 15, "topic_quiz": 20}
QUIZ_LIKE = ("quiz", "confirm", "retake")


def js_round(x: float) -> int:
    """Round half up, like JavaScript's Math.round (Python's round() rounds half to even)."""
    return floor(x + 0.5)


def avg(nums: list[float]) -> int:
    return js_round(sum(nums) / len(nums)) if nums else 0


@dataclass
class SubInfo:
    id: str
    title: str


@dataclass
class TopicInfo:
    id: str
    title: str
    subtopics: list[SubInfo]


@dataclass
class Task:
    type: str
    topic_id: str | None
    subtopic_id: str | None
    title: str
    minutes: int
    id: str = field(default_factory=new_id)
    day: int | None = None
    scheduled_for: date | None = None
    done: bool = False
    done_at: datetime | None = None
    result: str | None = None


def make_task(type_: str, topic_id: str | None, subtopic_id: str | None, title: str, minutes: int) -> Task:
    return Task(type=type_, topic_id=topic_id, subtopic_id=subtopic_id, title=title, minutes=minutes)


def build_tasks(topics: list[TopicInfo], pre_by_sub: dict[str, float], threshold: int) -> list[Task]:
    """Ordered task list from pre-test results.

    - Topics stay in syllabus order (later ideas build on earlier ones).
    - Within a topic the weakest sub-topics come first.
    - Sub-topics the student already knows only get a short confirmation quiz.
    - Each topic with several sub-topics ends with a topic quiz.
    """
    tasks: list[Task] = []
    for topic in topics:
        ordered = sorted(
            ((i, s, pre_by_sub.get(s.id, 0)) for i, s in enumerate(topic.subtopics)),
            key=lambda x: (x[2], x[0]),
        )
        for _, s, score in ordered:
            if score >= threshold:
                tasks.append(
                    make_task("confirm", topic.id, s.id, f"Confirm mastery: {s.title}", MINUTES["confirm"])
                )
            else:
                tasks.append(
                    make_task("study", topic.id, s.id, f"Study: {s.title}", 30 if score == 0 else MINUTES["study"])
                )
                tasks.append(make_task("quiz", topic.id, s.id, f"Quiz: {s.title}", MINUTES["quiz"]))
        if len(topic.subtopics) > 1:
            tasks.append(
                make_task("topic_quiz", topic.id, None, f"Topic quiz: {topic.title}", MINUTES["topic_quiz"])
            )
    return tasks


def repack(tasks: list[Task], start: date, today: date, minutes_per_day: int) -> int:
    """Assign calendar days to every unfinished task, in list order, from today onward.

    Honours the daily time budget (a single task longer than the budget gets a day to itself).
    Finished tasks keep the day they had. Returns how many unfinished tasks moved to a later day.
    """
    today_idx = max(0, (today - start).days)
    used: dict[int, int] = {}
    for t in tasks:
        if t.done and t.day is not None:
            used[t.day] = used.get(t.day, 0) + t.minutes
    day = today_idx
    moved = 0
    for t in tasks:
        if t.done:
            continue
        while used.get(day, 0) > 0 and used.get(day, 0) + t.minutes > minutes_per_day:
            day += 1
        if t.day is not None and day > t.day:
            moved += 1
        t.day = day
        t.scheduled_for = start + timedelta(days=day)
        used[day] = used.get(day, 0) + t.minutes
    return moved


def insert_later(tasks: list[Task], extra: list[Task], topic_id: str | None, skip: int) -> None:
    """Insert follow-up tasks after `skip` unfinished tasks.

    Never after the same topic's unfinished topic quiz, which must stay last.
    """
    seen = 0
    at = len(tasks)
    for i, t in enumerate(tasks):
        if t.done:
            continue
        seen += 1
        if seen == skip:
            at = i + 1
            break
    tq = next(
        (i for i, t in enumerate(tasks) if not t.done and t.type == "topic_quiz" and t.topic_id == topic_id),
        -1,
    )
    if tq != -1 and tq < at:
        at = tq
    tasks[at:at] = extra


def move_topic_quiz_last(tasks: list[Task], topic_id: str | None) -> None:
    """Keep a topic's unfinished topic quiz after all of that topic's other unfinished work."""
    tq = next(
        (t for t in tasks if not t.done and t.type == "topic_quiz" and t.topic_id == topic_id), None
    )
    if tq is None:
        return
    tasks.remove(tq)
    last = max(
        (i for i, t in enumerate(tasks) if not t.done and t.topic_id == topic_id), default=-1
    )
    tasks.insert(last + 1, tq)
