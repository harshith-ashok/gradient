"""Admin tools: users, roles and endpoints, logs, issues and system health."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models import User
from app.schemas.auth import Message
from app.schemas.ops import (
    AccessOut,
    IssueDetail,
    IssueList,
    IssueUpdate,
    LogList,
    ManagedUser,
    PasswordReset,
    SystemOut,
    UserCreate,
    UserList,
    UserUpdate,
)
from app.services import ops as svc

router = APIRouter(prefix="/admin", tags=["admin"])
admin = require_role("admin")
ERRORS = {400: {"model": Message}, 404: {"model": Message}}


def fail(e: svc.OpsError) -> HTTPException:
    return HTTPException(e.status_code, e.message)


# ---------------------------------------------------------------- users
@router.get("/users", response_model=UserList)
def users(q: str = "", role: Literal["student", "faculty", "admin"] | None = None,
          active: bool | None = None, page: int = Query(1, ge=1),
          page_size: int = Query(20, ge=1, le=svc.MAX_PAGE),
          db: Session = Depends(get_db), _: User = Depends(admin)):
    return svc.list_users(db, q, role, active, page, page_size)


@router.post("/users", response_model=ManagedUser, status_code=201, responses={**ERRORS, 409: {"model": Message}})
def create_user(body: UserCreate, db: Session = Depends(get_db), me: User = Depends(admin)):
    try:
        return svc.create_user(db, me, body.name, body.email, body.role, body.password)
    except svc.OpsError as e:
        raise fail(e) from e


@router.put("/users/{user_id}", response_model=ManagedUser, responses=ERRORS)
def update_user(user_id: str, body: UserUpdate, db: Session = Depends(get_db), me: User = Depends(admin)):
    try:
        return svc.update_user(db, me, user_id, body.name, body.role, body.is_active)
    except svc.OpsError as e:
        raise fail(e) from e


@router.post("/users/{user_id}/password", status_code=204, responses=ERRORS)
def reset_password(user_id: str, body: PasswordReset, db: Session = Depends(get_db), me: User = Depends(admin)):
    try:
        svc.reset_password(db, me, user_id, body.password)
    except svc.OpsError as e:
        raise fail(e) from e
    return Response(status_code=204)


# ---------------------------------------------------------------- roles and endpoints
@router.get("/access", response_model=AccessOut)
def access(request: Request, hours: int = Query(24, ge=1, le=720), db: Session = Depends(get_db),
           _: User = Depends(admin)):
    return svc.access_overview(db, request.app.state.routers, hours)


# ---------------------------------------------------------------- logs
@router.get("/logs", response_model=LogList)
def logs(level: Literal["INFO", "WARNING", "ERROR", "CRITICAL"] | None = None,
         kind: Literal["requests", "events"] | None = None, q: str = "", request_id: str = "",
         path: str = "", min_status: int | None = Query(None, ge=100, le=599), user_id: str = "",
         source: Literal["api", "worker", "judge"] | None = None, minutes: int | None = Query(None, ge=1, le=43200),
         page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=svc.MAX_PAGE),
         db: Session = Depends(get_db), _: User = Depends(admin)):
    return svc.list_logs(db, level=level, kind=kind, q=q, request_id_=request_id, path=path,
                         min_status=min_status, user_id=user_id, source=source, minutes=minutes,
                         page=page, page_size=page_size)


# ---------------------------------------------------------------- issues
@router.get("/issues", response_model=IssueList)
def issues(status: Literal["open", "resolved", "ignored"] | None = None, q: str = "",
           page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=svc.MAX_PAGE),
           db: Session = Depends(get_db), _: User = Depends(admin)):
    return svc.list_issues(db, status, q, page, page_size)


@router.get("/issues/{issue_id}", response_model=IssueDetail, responses=ERRORS)
def issue(issue_id: str, db: Session = Depends(get_db), _: User = Depends(admin)):
    try:
        return svc.issue_detail(db, issue_id)
    except svc.OpsError as e:
        raise fail(e) from e


@router.put("/issues/{issue_id}", response_model=IssueDetail, responses=ERRORS)
def update_issue(issue_id: str, body: IssueUpdate, db: Session = Depends(get_db), me: User = Depends(admin)):
    try:
        return svc.update_issue(db, me, issue_id, body.status, body.note)
    except svc.OpsError as e:
        raise fail(e) from e


# ---------------------------------------------------------------- system
@router.get("/system", response_model=SystemOut)
def system(db: Session = Depends(get_db), _: User = Depends(admin)):
    return svc.system(db)
