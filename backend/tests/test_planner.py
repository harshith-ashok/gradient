import random
from datetime import date, timedelta

import pytest

from app.services.planner import (
    MINUTES,
    SubInfo,
    TopicInfo,
    avg,
    build_tasks,
    insert_later,
    js_round,
    make_task,
    move_topic_quiz_last,
    repack,
)

START = date(2026, 1, 1)


def topics():
    return [
        TopicInfo("t1", "T1", [SubInfo("a", "A"), SubInfo("b", "B"), SubInfo("c", "C")]),
        TopicInfo("t2", "T2", [SubInfo("d", "D")]),
    ]


def test_js_round_is_half_up():
    assert [js_round(x) for x in (0.5, 1.5, 2.5, 62.5, 37.4)] == [1, 2, 3, 63, 37]
    assert avg([50, 75]) == 63 and avg([]) == 0


def test_build_tasks_orders_weakest_first_and_confirms_known():
    ts = build_tasks(topics(), {"a": 50, "b": 0, "c": 90, "d": 20}, 70)
    assert [(t.type, t.subtopic_id) for t in ts] == [
        ("study", "b"), ("quiz", "b"),          # weakest (0) first
        ("study", "a"), ("quiz", "a"),
        ("confirm", "c"),                       # already knows it: only a confirmation
        ("topic_quiz", None),                   # topic with several sub-topics ends with a quiz
        ("study", "d"), ("quiz", "d"),          # single sub-topic: no topic quiz
    ]
    assert ts[0].minutes == 30 and ts[2].minutes == MINUTES["study"]  # score 0 gets longer study


def test_build_tasks_ties_keep_syllabus_order():
    ts = build_tasks(topics(), {"a": 40, "b": 40, "c": 40, "d": 0}, 70)
    assert [t.subtopic_id for t in ts if t.type == "study"][:3] == ["a", "b", "c"]


def test_threshold_boundary_is_inclusive():
    only = [TopicInfo("t", "T", [SubInfo("x", "X")])]
    assert build_tasks(only, {"x": 70}, 70)[0].type == "confirm"
    assert build_tasks(only, {"x": 69}, 70)[0].type == "study"


def test_repack_respects_budget():
    ts = build_tasks(topics(), {}, 70)
    repack(ts, START, START, 60)
    per_day: dict[int, int] = {}
    for t in ts:
        per_day[t.day] = per_day.get(t.day, 0) + t.minutes
    assert all(m <= 60 for m in per_day.values())
    assert ts[0].scheduled_for == START and ts[-1].day >= 1


def test_oversized_task_gets_its_own_day():
    ts = [make_task("study", "t", "a", "big", 90), make_task("quiz", "t", "a", "q", 15)]
    repack(ts, START, START, 60)
    assert (ts[0].day, ts[1].day) == (0, 1)


def test_repack_moves_unfinished_forward_and_keeps_done():
    ts = build_tasks(topics(), {}, 70)
    repack(ts, START, START, 60)
    ts[0].done = True
    done_day = ts[0].day
    moved = repack(ts, START, START + timedelta(days=3), 60)
    assert ts[0].day == done_day  # finished work keeps its day
    assert all(t.day >= 3 for t in ts if not t.done)
    assert moved == sum(1 for t in ts if not t.done)


def test_repack_counts_only_tasks_pushed_later():
    ts = [make_task("study", "t", "a", "1", 30), make_task("quiz", "t", "a", "2", 30)]
    repack(ts, START, START, 60)
    assert repack(ts, START, START, 60) == 0
    assert repack(ts, START, START, 30) == 1  # second task no longer fits on day 0


def test_insert_later_skips_and_respects_topic_quiz():
    mk = lambda ty, i: make_task(ty, "t1", f"s{i}", f"{ty}{i}", 10)  # noqa: E731
    tq = make_task("topic_quiz", "t1", None, "TQ", 20)
    tasks = [mk("study", 1), mk("quiz", 1), mk("study", 2), mk("quiz", 2), tq]
    extra = [make_task("remediation", "t1", "s1", "R", 20)]
    insert_later(tasks, list(extra), "t1", 3)
    assert [t.title for t in tasks].index("R") == 3
    # skip larger than the list: goes before the topic quiz, never after
    tasks = [mk("study", 1), make_task("topic_quiz", "t1", None, "TQ", 20)]
    insert_later(tasks, list(extra), "t1", 9)
    assert [t.title for t in tasks] == ["study1", "R", "TQ"]


def test_insert_later_ignores_done_tasks_when_counting():
    a, b, c = (make_task("study", "t", "x", n, 10) for n in "abc")
    a.done = True
    tasks = [a, b, c]
    insert_later(tasks, [make_task("quiz", "t", "x", "NEW", 10)], "t", 1)
    assert [t.title for t in tasks] == ["a", "b", "NEW", "c"]


@pytest.mark.parametrize("seed", range(40))
def test_repack_invariants(seed):
    rng = random.Random(seed)
    budget = rng.choice([30, 45, 60, 90, 120])
    ts = [make_task("study", "t", f"s{i}", str(i), rng.choice([10, 15, 20, 25, 30])) for i in range(rng.randint(1, 25))]
    for t in ts:
        t.done = rng.random() < 0.3
    for t in ts:
        if t.done:
            t.day = rng.randint(0, 3)
    before = [(t.id, t.done, t.day) for t in ts]
    today = START + timedelta(days=rng.randint(0, 6))
    repack(ts, START, today, budget)

    assert [t.id for t in ts] == [b[0] for b in before]  # nothing lost or reordered
    for t, (_, done, day) in zip(ts, before, strict=True):
        if done:
            assert t.day == day  # done tasks untouched
    open_ = [t for t in ts if not t.done]
    assert all(t.day >= (today - START).days for t in open_)  # nothing scheduled in the past
    assert [t.day for t in open_] == sorted(t.day for t in open_)  # order preserved
    assert all(t.scheduled_for == START + timedelta(days=t.day) for t in open_)
    per_day: dict[int, int] = {}
    for t in ts:
        per_day[t.day] = per_day.get(t.day, 0) + t.minutes
    for d, m in per_day.items():
        members = [t for t in ts if t.day == d and not t.done]
        # a day may exceed the budget only through already-finished work or a lone oversized task
        done_m = sum(t.minutes for t in ts if t.day == d and t.done)
        if members and m > budget:
            assert done_m >= budget or len(members) == 1


def test_move_topic_quiz_last_puts_it_after_the_topics_open_work():
    a = make_task("study", "t1", "a", "A", 10)
    other = make_task("study", "t2", "x", "X", 10)
    tq = make_task("topic_quiz", "t1", None, "TQ", 20)
    b = make_task("quiz", "t1", "a", "B", 10)
    done = make_task("study", "t1", "a", "done", 10)
    done.done = True
    tasks = [done, tq, a, other, b]
    move_topic_quiz_last(tasks, "t1")
    assert [t.title for t in tasks] == ["done", "A", "X", "B", "TQ"]
    move_topic_quiz_last(tasks, "nope")  # no such topic quiz: no change, no error
    assert [t.title for t in tasks][-1] == "TQ"
