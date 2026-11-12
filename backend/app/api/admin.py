from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.admin import Overview, SettingsOut, SettingsUpdate, StudentDetailOut
from app.schemas.auth import Message
from app.services import admin as svc
from app.services import settings as settings_svc

router = APIRouter(prefix="/admin", tags=["admin"])
admin = require_role("admin")


@router.get("/overview", response_model=Overview)
def overview(
    q: str = "",
    course_id: str | None = None,
    status: Literal["on-track", "attention", "completed"] | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=svc.MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    _: User = Depends(admin),
):
    return svc.overview(db, q, course_id, status, page, page_size)


@router.get("/students/{student_id}", response_model=StudentDetailOut, responses={404: {"model": Message}})
def student(student_id: str, db: Session = Depends(get_db), _: User = Depends(admin)):
    try:
        return svc.student_detail(db, student_id)
    except svc.AdminError as e:
        raise HTTPException(e.status_code, e.message) from e


@router.get("/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), _: User = Depends(admin)):
    return settings_svc.settings_view(db)


@router.put("/settings", response_model=SettingsOut, responses={400: {"model": Message}, 404: {"model": Message}})
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db), _: User = Depends(admin)):
    try:
        return settings_svc.update_settings(db, body.global_threshold, body.per_course)
    except settings_svc.SettingsError as e:
        raise HTTPException(e.status_code, e.message) from e
