from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["student", "faculty", "admin"]
Level = Literal["INFO", "WARNING", "ERROR", "CRITICAL"]
IssueStatus = Literal["open", "resolved", "ignored"]


class Page(BaseModel):
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------- users
class ManagedUser(BaseModel):
    id: str
    name: str
    email: str
    role: Role
    is_active: bool
    student_id: str | None = None
    program: str | None = None
    department: str | None = None
    title: str | None = None
    created_at: datetime
    last_active: datetime | None = Field(None, description="Most recent API request by this user")


class UserList(Page):
    items: list[ManagedUser]
    by_role: dict[str, int]
    inactive: int


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    role: Role
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    role: Role | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)


# ---------------------------------------------------------------- roles and endpoints
class RoleInfo(BaseModel):
    role: Role
    description: str
    users: int
    active_users: int
    endpoints: int = Field(description="Endpoints this role can call")


class EndpointStats(BaseModel):
    requests: int = 0
    client_errors: int = 0
    server_errors: int = 0
    avg_ms: int = 0
    max_ms: int = 0
    last_called: datetime | None = None


class EndpointInfo(BaseModel):
    method: str
    path: str
    group: str
    summary: str
    access: Literal["public", "signed-in", "roles"]
    roles: list[Role] = Field(description="Roles that may call it (everyone for public and signed-in)")
    stats: EndpointStats


class AccessOut(BaseModel):
    roles: list[RoleInfo]
    endpoints: list[EndpointInfo]
    window_hours: int


# ---------------------------------------------------------------- logs
class LogOut(BaseModel):
    id: str
    ts: datetime
    level: Level
    source: str
    logger: str
    message: str
    request_id: str | None = None
    method: str | None = None
    path: str | None = None
    status: int | None = None
    duration_ms: int | None = None
    user_id: str | None = None
    user_name: str | None = None
    role: str | None = None


class LogList(Page):
    items: list[LogOut]


# ---------------------------------------------------------------- issues
class IssueOut(BaseModel):
    id: str
    title: str
    exc_type: str
    culprit: str
    source: str
    status: IssueStatus
    count: int
    first_seen: datetime
    last_seen: datetime
    note: str | None = None


class IssueEventOut(BaseModel):
    id: str
    ts: datetime
    message: str
    stack_trace: str
    request_id: str | None = None
    method: str | None = None
    path: str | None = None
    user_id: str | None = None
    user_name: str | None = None


class IssueDetail(IssueOut):
    events: list[IssueEventOut]


class IssueList(Page):
    items: list[IssueOut]
    by_status: dict[str, int]


class IssueUpdate(BaseModel):
    status: IssueStatus | None = None
    note: str | None = Field(None, max_length=500)


# ---------------------------------------------------------------- system
class Traffic(BaseModel):
    hour: datetime
    requests: int
    errors: int


class FailedJob(BaseModel):
    id: str
    type: str
    error: str | None = None
    created_at: datetime
    attempts: int


class SystemOut(BaseModel):
    checks: dict[str, str]
    environment: str
    llm_provider: str
    llm_model: str
    log_retention_days: int
    jobs: dict[str, int]
    failed_jobs: list[FailedJob]
    requests_24h: int
    client_errors_24h: int
    server_errors_24h: int
    avg_ms_24h: int
    open_issues: int
    traffic: list[Traffic]
    log_rows: int
