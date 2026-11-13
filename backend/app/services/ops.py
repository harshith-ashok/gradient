"""Admin operations: users, who-can-call-what, logs, issues and system health."""

import re
from datetime import timedelta

import redis as redis_lib
from fastapi.routing import APIRoute
from sqlalchemy import case, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.observability import request_id
from app.core.security import hash_password
from app.models import Issue, IssueEvent, Job, LogEntry, User
from app.models.base import ROLES, new_id, utcnow
from app.services import monitor

MAX_PAGE = 100
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LEVEL_ORDER = {"INFO": 0, "WARNING": 1, "ERROR": 2, "CRITICAL": 3}

ROLE_TEXT = {
    "student": "Studies courses, takes quizzes and tracks their own progress.",
    "faculty": "Uploads syllabi, reviews and edits course content, publishes courses.",
    "admin": "Sets pass marks, sees every student, manages users and the system.",
}


class OpsError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _page(page: int, size: int) -> tuple[int, int]:
    return max(1, page), min(max(1, size), MAX_PAGE)


def audit(db: Session, actor: User, message: str) -> None:
    """Who changed what, in the same log the dashboard shows."""
    db.add(LogEntry(level="INFO", source="api", logger="audit", message=monitor.scrub(message),
                    request_id=None if request_id.get() == "-" else request_id.get(),
                    user_id=actor.id, role=actor.role))
    db.commit()


# ------------------------------------------------------------------ users


def _user_out(u: User, last_active) -> dict:
    return {
        "id": u.id, "name": u.name, "email": u.email, "role": u.role, "is_active": u.is_active,
        "student_id": u.student_id, "program": u.program, "department": u.department, "title": u.title,
        "created_at": u.created_at, "last_active": last_active,
    }


def list_users(db: Session, q: str = "", role: str | None = None, active: bool | None = None,
               page: int = 1, page_size: int = 20) -> dict:
    page, page_size = _page(page, page_size)
    stmt = select(User)
    needle = q.strip().lower()
    if needle:
        like = f"%{needle}%"
        stmt = stmt.where(or_(func.lower(User.name).like(like), func.lower(User.email).like(like),
                              func.lower(func.coalesce(User.student_id, "")).like(like)))
    if role:
        stmt = stmt.where(User.role == role)
    if active is not None:
        stmt = stmt.where(User.is_active == active)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    users = list(db.scalars(stmt.order_by(User.role, User.name).offset((page - 1) * page_size).limit(page_size)))
    seen = dict(db.execute(
        select(LogEntry.user_id, func.max(LogEntry.ts))
        .where(LogEntry.user_id.in_([u.id for u in users]), LogEntry.method.is_not(None))
        .group_by(LogEntry.user_id)
    ).all()) if users else {}
    by_role = dict(db.execute(select(User.role, func.count()).group_by(User.role)).all())
    return {
        "items": [_user_out(u, seen.get(u.id)) for u in users], "total": total, "page": page,
        "page_size": page_size, "by_role": {r: by_role.get(r, 0) for r in ROLES},
        "inactive": db.scalar(select(func.count()).where(User.is_active.is_(False))) or 0,
    }


def _check_password(password: str) -> None:
    need = 8 if get_settings().env == "dev" else 12
    if len(password) < need:
        raise OpsError(f"Use a password of at least {need} characters.")


def _get_user(db: Session, user_id: str) -> User:
    u = db.get(User, user_id)
    if u is None:
        raise OpsError("User not found.", 404)
    return u


def _active_admins(db: Session) -> int:
    return db.scalar(select(func.count()).where(User.role == "admin", User.is_active.is_(True))) or 0


def create_user(db: Session, actor: User, name: str, email: str, role: str, password: str) -> dict:
    email = email.strip().lower()
    if not EMAIL.match(email):
        raise OpsError("That does not look like an email address.")
    _check_password(password)
    if db.scalar(select(User).where(User.email == email)):
        raise OpsError("An account with that email already exists.", 409)
    u = User(id=f"u-{new_id()[:10]}", name=name.strip(), email=email, role=role,
             password_hash=hash_password(password), is_active=True)
    db.add(u)
    db.commit()
    audit(db, actor, f"{actor.email} created {role} account {email}")
    return _user_out(u, None)


def update_user(db: Session, actor: User, user_id: str, name: str | None, role: str | None,
                is_active: bool | None) -> dict:
    u = _get_user(db, user_id)
    changes = []
    if name is not None and name.strip() != u.name:
        u.name = name.strip()
        changes.append("name")
    if role is not None and role != u.role:
        if u.id == actor.id:
            raise OpsError("You cannot change your own role.")
        if u.role == "admin" and u.is_active and _active_admins(db) <= 1:
            raise OpsError("This is the last active admin; make another admin first.")
        changes.append(f"role {u.role}→{role}")
        u.role = role
    if is_active is not None and is_active != u.is_active:
        if not is_active and u.id == actor.id:
            raise OpsError("You cannot deactivate your own account.")
        if not is_active and u.role == "admin" and _active_admins(db) <= 1:
            raise OpsError("This is the last active admin; make another admin first.")
        u.is_active = is_active
        changes.append("activated" if is_active else "deactivated")
    db.commit()
    if changes:
        audit(db, actor, f"{actor.email} changed {u.email}: {', '.join(changes)}")
    return _user_out(u, None)


def reset_password(db: Session, actor: User, user_id: str, password: str) -> None:
    u = _get_user(db, user_id)
    _check_password(password)
    u.password_hash = hash_password(password)
    db.commit()
    audit(db, actor, f"{actor.email} reset the password of {u.email}")


# ------------------------------------------------------------------ roles and endpoints


def _calls(dep):
    for d in dep.dependencies:
        yield d.call
        yield from _calls(d)


def endpoint_registry(routers) -> list[dict]:
    """Every route with who may call it, read from the real dependencies (so it cannot drift)."""
    out = []
    for router, prefix in routers:
        for r in router.routes:
            if not isinstance(r, APIRoute):
                continue
            calls = list(_calls(r.dependant))
            allowed = next((c.allowed_roles for c in calls if hasattr(c, "allowed_roles")), None)
            if allowed:
                access, roles = "roles", list(allowed)
            elif get_current_user in calls:
                access, roles = "signed-in", list(ROLES)
            else:
                access, roles = "public", list(ROLES)
            group = (r.tags[0] if r.tags else prefix.strip("/")) or "api"
            for method in sorted(r.methods - {"HEAD", "OPTIONS"}):
                out.append({"method": method, "path": prefix + r.path, "group": str(group),
                            "summary": r.summary or r.name.replace("_", " ").capitalize(),
                            "access": access, "roles": roles})
    return sorted(out, key=lambda e: (e["group"], e["path"], e["method"]))


def access_overview(db: Session, routers, hours: int = 24) -> dict:
    hours = min(max(1, hours), 24 * 30)
    since = utcnow() - timedelta(hours=hours)
    rows = db.execute(
        select(
            LogEntry.method, LogEntry.path, func.count(),
            func.sum(case((LogEntry.status.between(400, 499), 1), else_=0)),
            func.sum(case((LogEntry.status >= 500, 1), else_=0)),
            func.avg(LogEntry.duration_ms), func.max(LogEntry.duration_ms), func.max(LogEntry.ts),
        ).where(LogEntry.method.is_not(None), LogEntry.ts >= since).group_by(LogEntry.method, LogEntry.path)
    ).all()
    stats = {(m, p): {"requests": n, "client_errors": int(c4 or 0), "server_errors": int(c5 or 0),
                      "avg_ms": round(avg or 0), "max_ms": mx or 0, "last_called": last}
             for m, p, n, c4, c5, avg, mx, last in rows}
    endpoints = endpoint_registry(routers)
    for e in endpoints:
        e["stats"] = stats.get((e["method"], e["path"]), {})
    users = dict(db.execute(select(User.role, func.count()).group_by(User.role)).all())
    active = dict(db.execute(select(User.role, func.count()).where(User.is_active.is_(True)).group_by(User.role)).all())
    roles = [{
        "role": r, "description": ROLE_TEXT[r], "users": users.get(r, 0), "active_users": active.get(r, 0),
        "endpoints": sum(1 for e in endpoints if r in e["roles"]),
    } for r in ROLES]
    return {"roles": roles, "endpoints": endpoints, "window_hours": hours}


# ------------------------------------------------------------------ logs


def _names(db: Session, ids) -> dict[str, str]:
    ids = {i for i in ids if i}
    return dict(db.execute(select(User.id, User.name).where(User.id.in_(ids))).all()) if ids else {}


def list_logs(db: Session, *, level: str | None = None, kind: str | None = None, q: str = "",
              request_id_: str = "", path: str = "", min_status: int | None = None, user_id: str = "",
              source: str | None = None, minutes: int | None = None, page: int = 1, page_size: int = 50) -> dict:
    page, page_size = _page(page, page_size)
    stmt = select(LogEntry)
    if level:
        stmt = stmt.where(LogEntry.level.in_([k for k, v in LEVEL_ORDER.items() if v >= LEVEL_ORDER[level]]))
    if kind == "requests":
        stmt = stmt.where(LogEntry.method.is_not(None))
    elif kind == "events":
        stmt = stmt.where(LogEntry.method.is_(None))
    if q.strip():
        stmt = stmt.where(func.lower(LogEntry.message).like(f"%{q.strip().lower()}%"))
    if request_id_.strip():
        stmt = stmt.where(LogEntry.request_id == request_id_.strip())
    if path.strip():
        stmt = stmt.where(LogEntry.path.like(f"%{path.strip()}%"))
    if min_status:
        stmt = stmt.where(LogEntry.status >= min_status)
    if user_id.strip():
        stmt = stmt.where(LogEntry.user_id == user_id.strip())
    if source:
        stmt = stmt.where(LogEntry.source == source)
    if minutes:
        stmt = stmt.where(LogEntry.ts >= utcnow() - timedelta(minutes=minutes))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    ordered = stmt.order_by(LogEntry.ts.desc(), LogEntry.id).offset((page - 1) * page_size).limit(page_size)
    rows = list(db.scalars(ordered))
    names = _names(db, (r.user_id for r in rows))
    items = [{**{c: getattr(r, c) for c in ("id", "ts", "level", "source", "logger", "message", "request_id",
                                              "method", "path", "status", "duration_ms", "user_id", "role")},
              "user_name": names.get(r.user_id)} for r in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ------------------------------------------------------------------ issues


def list_issues(db: Session, status: str | None = None, q: str = "", page: int = 1, page_size: int = 20) -> dict:
    page, page_size = _page(page, page_size)
    stmt = select(Issue)
    if status:
        stmt = stmt.where(Issue.status == status)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(Issue.title).like(like), func.lower(Issue.culprit).like(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(Issue.last_seen.desc()).offset((page - 1) * page_size).limit(page_size)))
    counts = dict(db.execute(select(Issue.status, func.count()).group_by(Issue.status)).all())
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "by_status": {s: counts.get(s, 0) for s in ("open", "resolved", "ignored")}}


def issue_detail(db: Session, issue_id: str) -> dict:
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise OpsError("Issue not found.", 404)
    events = list(db.scalars(select(IssueEvent).where(IssueEvent.issue_id == issue.id)
                             .order_by(IssueEvent.ts.desc()).limit(monitor.MAX_EVENTS_PER_ISSUE)))
    names = _names(db, (e.user_id for e in events))
    return {
        **{c: getattr(issue, c) for c in ("id", "title", "exc_type", "culprit", "source", "status", "count",
                                          "first_seen", "last_seen", "note")},
        "events": [{**{c: getattr(e, c) for c in ("id", "ts", "message", "stack_trace", "request_id", "method",
                                                   "path", "user_id")}, "user_name": names.get(e.user_id)}
                   for e in events],
    }


def update_issue(db: Session, actor: User, issue_id: str, status: str | None, note: str | None) -> dict:
    issue = db.get(Issue, issue_id)
    if issue is None:
        raise OpsError("Issue not found.", 404)
    if status and status != issue.status:
        issue.status = status
        audit(db, actor, f"{actor.email} marked issue “{issue.title[:80]}” as {status}")
    if note is not None:
        issue.note = note.strip() or None
    db.commit()
    return issue_detail(db, issue_id)


# ------------------------------------------------------------------ system


def system(db: Session) -> dict:
    s = get_settings()
    checks: dict[str, str] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:  # noqa: BLE001
        checks["postgres"] = "down"
    try:
        redis_lib.Redis.from_url(s.redis_url, socket_connect_timeout=1).ping()
        checks["redis"] = "ok"
    except Exception:  # noqa: BLE001
        checks["redis"] = "down"

    from app.services import judge  # late: it pulls in the sandbox client

    checks["code runner"] = "ok" if judge.alive() else "down"

    now = utcnow()
    since = now - timedelta(hours=24)
    req = (LogEntry.method.is_not(None), LogEntry.ts >= since)
    total, c4, c5, avg = db.execute(select(
        func.count(), func.sum(case((LogEntry.status.between(400, 499), 1), else_=0)),
        func.sum(case((LogEntry.status >= 500, 1), else_=0)), func.avg(LogEntry.duration_ms),
    ).where(*req)).one()

    start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=23)
    buckets = {start + timedelta(hours=i): [0, 0] for i in range(24)}
    for ts, status in db.execute(select(LogEntry.ts, LogEntry.status).where(*req).limit(100_000)):
        ts = ts if ts.tzinfo else ts.replace(tzinfo=now.tzinfo)
        key = ts.replace(minute=0, second=0, microsecond=0)
        if key in buckets:
            buckets[key][0] += 1
            buckets[key][1] += 1 if status and status >= 500 else 0

    jobs = dict(db.execute(select(Job.status, func.count()).group_by(Job.status)).all())
    failed = list(db.scalars(select(Job).where(Job.status == "failed").order_by(Job.created_at.desc()).limit(10)))
    return {
        "checks": checks, "environment": s.env, "llm_provider": s.llm_provider, "llm_model": s.llm_model,
        "log_retention_days": s.log_retention_days,
        "jobs": {k: jobs.get(k, 0) for k in ("queued", "running", "succeeded", "failed")},
        "failed_jobs": [{"id": j.id, "type": j.type, "error": j.error, "created_at": j.created_at,
                         "attempts": j.attempts} for j in failed],
        "requests_24h": total or 0, "client_errors_24h": int(c4 or 0), "server_errors_24h": int(c5 or 0),
        "avg_ms_24h": round(avg or 0),
        "open_issues": db.scalar(select(func.count()).where(Issue.status == "open")) or 0,
        "traffic": [{"hour": h, "requests": v[0], "errors": v[1]} for h, v in buckets.items()],
        "log_rows": db.scalar(select(func.count()).select_from(LogEntry)) or 0,
    }
