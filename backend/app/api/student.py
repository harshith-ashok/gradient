from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.auth import Message
from app.schemas.learning import (
    CatalogItem,
    CompleteResult,
    CompleteSubtopicRequest,
    CourseHistory,
    Dashboard,
    EnrollmentDetail,
    PlanMinutesRequest,
    PracticeCourse,
    Progress,
    QuizResult,
    QuizStart,
    QuizStartRequest,
    QuizSubmitRequest,
    StudentCourse,
    StudentSubtopicView,
)
from app.services import courses as course_svc
from app.services import learning as svc

router = APIRouter(prefix="/student", tags=["student"])
student = require_role("student")
ERR = {404: {"model": Message}, 400: {"model": Message}}


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (svc.LearningError, course_svc.CourseError) as e:
        raise HTTPException(e.status_code, e.message) from e


@router.get("/catalog", response_model=list[CatalogItem])
def catalog(db: Session = Depends(get_db), user: User = Depends(student)):
    return svc.catalog(db, user)


@router.get("/courses/{course_id}", response_model=StudentCourse, responses=ERR)
def course(course_id: str, db: Session = Depends(get_db), user: User = Depends(student)):
    return _guard(svc.student_course, db, user, course_id)


@router.get(
    "/courses/{course_id}/subtopics/{subtopic_id}", response_model=StudentSubtopicView, responses=ERR
)
def subtopic(course_id: str, subtopic_id: str, db: Session = Depends(get_db),
             user: User = Depends(student)):
    return _guard(svc.subtopic_view, db, user, course_id, subtopic_id)


@router.post("/courses/{course_id}/subtopics/{subtopic_id}/complete", response_model=CompleteResult,
             responses=ERR)
def complete_subtopic(course_id: str, subtopic_id: str, body: CompleteSubtopicRequest,
                      db: Session = Depends(get_db), user: User = Depends(student)):
    return _guard(svc.complete_subtopic_task, db, user, course_id, subtopic_id, body.type)


@router.post("/courses/{course_id}/tasks/{task_id}/complete", response_model=CompleteResult,
             responses=ERR)
def complete_task(course_id: str, task_id: str, db: Session = Depends(get_db),
                  user: User = Depends(student)):
    return _guard(svc.complete_task, db, user, course_id, task_id)


@router.put("/courses/{course_id}/plan", response_model=EnrollmentDetail, responses=ERR)
def set_plan_minutes(course_id: str, body: PlanMinutesRequest, db: Session = Depends(get_db),
                     user: User = Depends(student)):
    return _guard(svc.update_plan_settings, db, user, course_id,
                  body.minutes_per_day, body.target_days)


@router.post("/quizzes", response_model=QuizStart, responses=ERR)
def start_quiz(body: QuizStartRequest, db: Session = Depends(get_db), user: User = Depends(student)):
    return _guard(svc.start_quiz, db, user, body.course_id, body.kind, body.topic_id, body.subtopic_id)


@router.post("/quizzes/{quiz_id}/submit", response_model=QuizResult,
             responses={**ERR, 410: {"model": Message}})
def submit_quiz(quiz_id: str, body: QuizSubmitRequest, db: Session = Depends(get_db),
                user: User = Depends(student)):
    return _guard(svc.submit_quiz, db, user, quiz_id, body.answers)


@router.get("/dashboard", response_model=Dashboard)
def dashboard(db: Session = Depends(get_db), user: User = Depends(student)):
    return svc.dashboard(db, user)


@router.get("/progress", response_model=Progress)
def progress(db: Session = Depends(get_db), user: User = Depends(student)):
    return svc.progress(db, user)


@router.get("/practice", response_model=list[PracticeCourse])
def practice(db: Session = Depends(get_db), user: User = Depends(student)):
    return svc.practice_options(db, user)


@router.get("/history", response_model=list[CourseHistory])
def history(db: Session = Depends(get_db), user: User = Depends(student)):
    return svc.history(db, user)
