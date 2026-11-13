"""Coding challenges: students solve them, faculty write them."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.auth import Message
from app.schemas.coding import (
    ProblemBrief,
    ProblemDetail,
    ProblemFull,
    ProblemIn,
    StaffRunRequest,
    SubmissionBrief,
    SubmissionCreated,
    SubmissionOut,
    SubmitRequest,
)
from app.services import coding as svc
from app.services.courses import CourseError

router = APIRouter(tags=["coding"])
student = require_role("student")
staff = require_role("faculty", "admin")
ERRORS = {400: {"model": Message}, 403: {"model": Message}, 404: {"model": Message}, 413: {"model": Message},
          429: {"model": Message}}


def _guard(fn, *args):
    try:
        return fn(*args)
    except CourseError as e:
        raise HTTPException(e.status_code, e.message) from e


# ---------------------------------------------------------------- students
@router.get("/student/subtopics/{subtopic_id}/problems", response_model=list[ProblemBrief], responses=ERRORS)
def problems(subtopic_id: str, db: Session = Depends(get_db), user: User = Depends(student)):
    return _guard(svc.student_list, db, user, subtopic_id)


@router.get("/student/problems/{problem_id}", response_model=ProblemDetail, responses=ERRORS)
def problem(problem_id: str, db: Session = Depends(get_db), user: User = Depends(student)):
    return _guard(svc.student_detail, db, user, problem_id)


@router.post("/student/problems/{problem_id}/submit", response_model=SubmissionCreated, status_code=202,
             responses=ERRORS)
def submit(problem_id: str, body: SubmitRequest, db: Session = Depends(get_db), user: User = Depends(student)):
    """Queue code to run. Poll the submission; `run` checks the sample tests, `submit` all of them."""
    return _guard(svc.student_submit, db, user, problem_id, body.language, body.code, body.mode)


@router.get("/student/problems/{problem_id}/submissions", response_model=list[SubmissionBrief], responses=ERRORS)
def history(problem_id: str, db: Session = Depends(get_db), user: User = Depends(student)):
    return _guard(svc.student_history, db, user, problem_id)


@router.get("/student/submissions/{submission_id}", response_model=SubmissionOut, responses=ERRORS)
def submission(submission_id: str, db: Session = Depends(get_db), user: User = Depends(student)):
    return _guard(svc.student_submission, db, user, submission_id)


# ---------------------------------------------------------------- faculty
@router.get("/faculty/subtopics/{subtopic_id}/problems", response_model=list[ProblemFull], responses=ERRORS)
def staff_problems(subtopic_id: str, db: Session = Depends(get_db), user: User = Depends(staff)):
    return _guard(svc.staff_list, db, user, subtopic_id)


@router.post("/faculty/subtopics/{subtopic_id}/problems", response_model=ProblemFull, status_code=201,
             responses=ERRORS)
def create_problem(subtopic_id: str, body: ProblemIn, db: Session = Depends(get_db), user: User = Depends(staff)):
    return _guard(svc.staff_create, db, user, subtopic_id, body)


@router.put("/faculty/problems/{problem_id}", response_model=ProblemFull, responses=ERRORS)
def update_problem(problem_id: str, body: ProblemIn, db: Session = Depends(get_db), user: User = Depends(staff)):
    return _guard(svc.staff_update, db, user, problem_id, body)


@router.delete("/faculty/problems/{problem_id}", status_code=204, responses=ERRORS)
def delete_problem(problem_id: str, db: Session = Depends(get_db), user: User = Depends(staff)):
    _guard(svc.staff_delete, db, user, problem_id)
    return Response(status_code=204)


@router.post("/faculty/problems/{problem_id}/test-run", response_model=SubmissionCreated, status_code=202,
             responses=ERRORS)
def staff_run(problem_id: str, body: StaffRunRequest, db: Session = Depends(get_db), user: User = Depends(staff)):
    """Run a reference solution against every test, with full detail, to check the tests are right."""
    return _guard(svc.staff_run, db, user, problem_id, body.language, body.code)


@router.get("/faculty/submissions/{submission_id}", response_model=SubmissionOut, responses=ERRORS)
def staff_submission(submission_id: str, db: Session = Depends(get_db), user: User = Depends(staff)):
    return _guard(svc.staff_submission, db, user, submission_id)
