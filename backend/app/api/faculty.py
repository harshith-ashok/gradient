from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.admin import Overview, StudentDetailOut
from app.schemas.auth import Message
from app.schemas.course import (
    CourseFull,
    CourseSave,
    QuestionImportReport,
    StaffCourseItem,
    StatusChange,
    StatusOut,
)
from app.services import admin as admin_svc
from app.services import courses as svc
from app.services import question_sheet as sheet

router = APIRouter(prefix="/faculty", tags=["faculty"])
staff = require_role("faculty", "admin")
ERRORS = {403: {"model": Message}, 404: {"model": Message}, 400: {"model": Message}}


def _guard(fn, *args):
    try:
        return fn(*args)
    except svc.CourseError as e:
        raise HTTPException(e.status_code, e.message) from e


@router.get("/students", response_model=Overview)
def students_overview(
    q: str = "",
    course_id: str | None = None,
    status: Literal["on-track", "attention", "completed"] | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=admin_svc.MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    user: User = Depends(staff),
):
    """Progress of the students enrolled in the caller's own courses (admins see their own too)."""
    return admin_svc.overview(db, q, course_id, status, page, page_size, owner_id=user.id)


@router.get("/students/{student_id}", response_model=StudentDetailOut, responses={404: {"model": Message}})
def student_progress(student_id: str, db: Session = Depends(get_db), user: User = Depends(staff)):
    try:
        return admin_svc.student_detail(db, student_id, owner_id=user.id)
    except admin_svc.AdminError as e:
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


def _xlsx(data: bytes, filename: str) -> Response:
    return Response(data, media_type=sheet.XLSX,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/questions/template.xlsx", responses={200: {"content": {sheet.XLSX: {}}}})
def questions_template(_: User = Depends(staff)):
    """An empty question sheet with two example rows and instructions."""
    return _xlsx(sheet.template(), "questions-template.xlsx")


@router.get("/courses/{course_id}/questions.xlsx", responses={**ERRORS, 200: {"content": {sheet.XLSX: {}}}})
def export_questions(course_id: str, db: Session = Depends(get_db), user: User = Depends(staff)):
    """Every quiz question of the course as an Excel sheet (one row per question)."""
    data, name = _guard(sheet.export_course, db, user, course_id)
    return _xlsx(data, name)


@router.post("/courses/{course_id}/questions/import", response_model=QuestionImportReport,
             responses={**ERRORS, 413: {"model": Message}})
async def import_questions(
    course_id: str,
    file: UploadFile = File(...),
    mode: Literal["merge", "replace"] = Form("merge"),
    dry_run: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(staff),
):
    """Import questions from an .xlsx sheet. All or nothing: any bad row means nothing is saved.
    Use dry_run to check a file first."""
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)  # never buffer more than the limit
    return _guard(sheet.import_sheet, db, user, course_id, data, mode, dry_run)
