from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.auth import Message
from app.schemas.course import CourseFull, CourseSave, StaffCourseItem, StatusChange, StatusOut
from app.services import courses as svc

router = APIRouter(prefix="/faculty", tags=["faculty"])
staff = require_role("faculty", "admin")
ERRORS = {403: {"model": Message}, 404: {"model": Message}, 400: {"model": Message}}


def _guard(fn, *args):
    try:
        return fn(*args)
    except svc.CourseError as e:
        raise HTTPException(e.status_code, e.message) from e


@router.get("/courses", response_model=list[StaffCourseItem])
def list_courses(db: Session = Depends(get_db), user: User = Depends(staff)):
    return svc.list_for_staff(db, user)


@router.get("/courses/{course_id}", response_model=CourseFull, responses=ERRORS)
def get_course(course_id: str, db: Session = Depends(get_db), user: User = Depends(staff)):
    return _guard(svc.get_for_staff, db, user, course_id)


@router.put("/courses/{course_id}", response_model=CourseFull, responses=ERRORS)
def save_course(
    course_id: str, body: CourseSave, db: Session = Depends(get_db), user: User = Depends(staff)
):
    return _guard(svc.save_course, db, user, course_id, body)


@router.post("/courses/{course_id}/status", response_model=StatusOut, responses=ERRORS)
def set_status(
    course_id: str, body: StatusChange, db: Session = Depends(get_db), user: User = Depends(staff)
):
    return _guard(svc.set_status, db, user, course_id, body.status)
