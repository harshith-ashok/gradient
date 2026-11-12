from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.agents.llm import get_llm
from app.core.db import get_db
from app.core.deps import require_role
from app.models import Job, User
from app.schemas.ai import (
    AIHealth,
    DeriveRequest,
    GenerateRequest,
    JobOut,
    JobQueued,
    UploadCreated,
    UploadOut,
)
from app.schemas.auth import Message
from app.services import courses as course_svc
from app.services import syllabus as svc

staff = require_role("faculty", "admin")
router = APIRouter(tags=["ai"])
ERR = {400: {"model": Message}, 403: {"model": Message}, 404: {"model": Message}, 409: {"model": Message},
       413: {"model": Message}, 415: {"model": Message}}


def _guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except course_svc.CourseError as e:
        raise HTTPException(e.status_code, e.message) from e


def _job_out(j: Job | None) -> dict | None:
    if j is None:
        return None
    return {"id": j.id, "type": j.type, "status": j.status, "course_id": j.course_id, "upload_id": j.upload_id,
            "progress": j.progress or {}, "result": j.result, "error": j.error, "created_at": j.created_at,
            "started_at": j.started_at, "finished_at": j.finished_at}


def _upload_out(db: Session, up) -> dict:
    return {"id": up.id, "course_id": up.course_id, "file_name": up.file_name, "status": up.status,
            "ocr_used": up.ocr_used, "indexed": up.indexed, "characters": len(up.extracted_text or ""),
            "topics": up.topics, "error": up.error, "job": _job_out(svc.latest_job(db, up.id))}


@router.post("/faculty/syllabus", response_model=UploadCreated, status_code=202, responses=ERR)
async def upload_syllabus(
    course_code: str = Form(...),
    course_title: str = Form(...),
    department: str | None = Form(None),
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(staff),
):
    """Start analysing a syllabus (file or pasted text). Creates a draft course; poll the job."""
    data = None
    if file is not None and file.filename:
        limit = svc.get_settings().max_upload_mb * 1024 * 1024
        data = await file.read(limit + 1)  # never buffer more than the limit
    course, up, job = _guard(
        svc.create_upload, db, user, code=course_code, title=course_title, department=department,
        file_name=file.filename if file is not None else None, data=data, text=text,
    )
    db.commit()
    return {"course_id": course.id, "upload_id": up.id, "job_id": job.id}


@router.get("/faculty/syllabus/{upload_id}", response_model=UploadOut, responses=ERR)
def get_upload(upload_id: str, db: Session = Depends(get_db), user: User = Depends(staff)):
    return _upload_out(db, _guard(svc.owned_upload, db, user, upload_id))


@router.post("/faculty/syllabus/{upload_id}/derive", response_model=JobQueued, status_code=202, responses=ERR)
def derive(upload_id: str, body: DeriveRequest, db: Session = Depends(get_db), user: User = Depends(staff)):
    job = _guard(svc.request_derive, db, user, upload_id, body.topics, body.replace)
    return {"job_id": job.id}


@router.post("/faculty/courses/{course_id}/generate", response_model=JobQueued, status_code=202, responses=ERR)
def generate(course_id: str, body: GenerateRequest, db: Session = Depends(get_db), user: User = Depends(staff)):
    job = _guard(svc.request_generate, db, user, course_id, body.subtopic_ids, body.levels, body.force)
    return {"job_id": job.id}


@router.get("/jobs/{job_id}", response_model=JobOut, responses=ERR)
def get_job(job_id: str, db: Session = Depends(get_db), user: User = Depends(staff)):
    job = db.get(Job, job_id)
    if job is None or (user.role != "admin" and job.created_by != user.id):
        raise HTTPException(404, "Job not found.")
    return _job_out(job)


@router.get("/faculty/ai/health", response_model=AIHealth)
def ai_health(_: User = Depends(staff)):
    """Is the model server reachable, and are the configured models installed?"""
    return get_llm().health()
