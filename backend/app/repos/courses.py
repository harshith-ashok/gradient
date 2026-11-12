from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Course, Enrollment, Subtopic, Topic, User


def _tree_options():
    return (
        selectinload(Course.topics)
        .selectinload(Topic.subtopics)
        .options(
            selectinload(Subtopic.flashcards),
            selectinload(Subtopic.questions),
            selectinload(Subtopic.remediation),
        )
    )


def get_with_tree(db: Session, course_id: str) -> Course | None:
    return db.scalar(select(Course).where(Course.id == course_id).options(_tree_options()))


def list_published(db: Session) -> list[Course]:
    return list(
        db.scalars(
            select(Course)
            .where(Course.status == "published")
            .options(selectinload(Course.topics).selectinload(Topic.subtopics))
            .order_by(Course.code)
        )
    )


def list_for_staff(db: Session, user: User) -> list[Course]:
    q = select(Course).options(selectinload(Course.topics).selectinload(Topic.subtopics))
    if user.role != "admin":
        q = q.where(Course.owner_id == user.id)
    return list(db.scalars(q.order_by(Course.code)))


def enrolled_counts(db: Session, course_ids: list[str]) -> dict[str, int]:
    if not course_ids:
        return {}
    rows = db.execute(
        select(Enrollment.course_id, func.count())
        .where(Enrollment.course_id.in_(course_ids))
        .group_by(Enrollment.course_id)
    )
    return {cid: n for cid, n in rows}


def user_names(db: Session, ids: set[str]) -> dict[str, str]:
    if not ids:
        return {}
    return {u.id: u.name for u in db.scalars(select(User).where(User.id.in_(ids)))}


def all_with_structure(db: Session) -> list[Course]:
    """Every course (drafts included) with topics and sub-topics only: enough for progress maths."""
    return list(
        db.scalars(select(Course).options(selectinload(Course.topics).selectinload(Topic.subtopics)).order_by(Course.code))
    )
