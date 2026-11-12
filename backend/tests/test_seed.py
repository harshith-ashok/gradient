from sqlalchemy import func, select

from app.models import Course, Flashcard, Question, Setting, Subtopic, User
from app.seed import run as seed


def test_seed_contents(db):
    assert db.scalar(select(func.count(User.id))) == 10
    assert db.scalar(select(func.count(Course.id))) == 3
    assert db.scalar(select(func.count(Subtopic.id))) == 17
    assert db.scalar(select(func.count(Flashcard.id))) > 40
    assert db.get(Setting, "pass_mark").value == 70


def test_seed_is_idempotent(db):
    assert seed.run(db, history=False) == {"users": 0, "courses": 0}
    assert db.scalar(select(func.count(User.id))) == 10


def test_questions_have_valid_answer_index(db):
    for q in db.scalars(select(Question)):
        assert 0 <= q.answer_index < len(q.options)


def test_passwords_are_hashed(db):
    assert all(u.password_hash.startswith("$argon2") for u in db.scalars(select(User)))
