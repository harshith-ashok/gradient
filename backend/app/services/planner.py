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
    note: str | None = None


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


# ------------------------------------------------------- AI proposal and the time window

MIN_FLEX = 10  # shortest a study or remediation session may be squeezed to
MAX_STUDY = 90
RESERVE = 0.15  # share of the window kept free for retakes and remediation after future failures
FLEX = ("study", "remediation")


def apply_proposal(tasks: list[Task], proposal: dict[str, dict]) -> None:
    """Apply a (validated) per-sub-topic proposal to the unfinished tasks.

    A proposal can only change how long each study session is and the order of a topic's sub-topics.
    It can never add or remove a task, so everything in the syllabus stays in the plan.
    proposal[sub_id] = {"minutes": int, "priority": int}
    """
    seen: set[str | None] = set()
    for t in tasks:
        if t.done or t.type != "study" or t.subtopic_id in seen:
            continue
        p = proposal.get(t.subtopic_id or "")
        if p:
            t.minutes = max(MIN_FLEX, min(MAX_STUDY, int(p["minutes"])))
            seen.add(t.subtopic_id)
    topics: dict[str | None, list[int]] = {}
    for i, t in enumerate(tasks):
        if not t.done and t.type != "topic_quiz":
            topics.setdefault(t.topic_id, []).append(i)
    for idxs in topics.values():
        groups: dict[str | None, list[Task]] = {}
        for i in idxs:
            groups.setdefault(tasks[i].subtopic_id, []).append(tasks[i])
        rank = {sid: (proposal[sid]["priority"] if sid in proposal else 1000 + n)
                for n, sid in enumerate(groups)}
        flat = [t for sid in sorted(groups, key=lambda s: (rank[s], list(groups).index(s))) for t in groups[sid]]
        for i, t in zip(idxs, flat, strict=True):
            tasks[i] = t


def window_stats(tasks: list[Task], start: date, today: date, minutes_per_day: int,
                 target_days: int) -> tuple[int, int, int]:
    """(days left, minutes left in the time frame, minutes of quizzes that cannot shrink)."""
    today_idx = max(0, (today - start).days)
    days_left = max(1, target_days - today_idx)
    used_today = sum(t.minutes for t in tasks if t.done and t.day == today_idx)
    window = max(0, days_left * minutes_per_day - used_today)
    fixed = sum(t.minutes for t in tasks if not t.done and t.type not in FLEX)
    return days_left, window, fixed


@dataclass
class Fit:
    fits: bool  # does everything unfinished end inside the time frame?
    last_day: int  # 0-based day of the last unfinished task
    target_days: int
    needed_minutes_per_day: int  # the least daily time that could still cover everything
    shrunk: int  # study sessions shortened to make it fit
    moved: int = 0  # unfinished tasks that ended up on a later day than before


def fit_window(tasks: list[Task], start: date, today: date, minutes_per_day: int, target_days: int,
               reserve: float = RESERVE) -> Fit:
    """Schedule the unfinished tasks so the whole syllabus finishes inside the time frame.

    Nothing is ever dropped. When the work is more than the window holds, study and remediation
    sessions are shortened (never below MIN_FLEX) and the quizzes stay as they are. If it still does
    not fit, the plan runs past the deadline and `fits` is False, with the daily time that would work.
    """
    today_idx = max(0, (today - start).days)
    open_ = [t for t in tasks if not t.done]
    days_left, window, fixed = window_stats(tasks, start, today, minutes_per_day, target_days)
    flex = [t for t in open_ if t.type in FLEX]
    shrunk: set[str] = set()
    before = {t.id: t.day for t in open_}

    def squeeze(factor: float) -> None:
        for t in flex:
            new = max(MIN_FLEX, int(t.minutes * factor) // 5 * 5)
            if new < t.minutes:
                t.minutes = new
                shrunk.add(t.id)

    flex_total = sum(t.minutes for t in flex)
    allowed = max(window * (1 - reserve) - fixed, len(flex) * MIN_FLEX)
    if flex_total > allowed:
        squeeze(allowed / flex_total)
    repack(tasks, start, today, minutes_per_day)
    for _ in range(15):
        last = max((t.day or 0 for t in open_), default=today_idx)
        if last < target_days or all(t.minutes <= MIN_FLEX for t in flex):
            break
        squeeze(0.9)
        repack(tasks, start, today, minutes_per_day)
    last = max((t.day or 0 for t in open_), default=today_idx)
    floor_total = fixed + len(flex) * MIN_FLEX
    return Fit(
        fits=last < target_days, last_day=last, target_days=target_days,
        needed_minutes_per_day=-(-floor_total // days_left), shrunk=len(shrunk),
        moved=sum(1 for t in open_ if before[t.id] is not None and (t.day or 0) > before[t.id]),
    )
