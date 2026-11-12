"""Background job queue on Postgres. The API enqueues; the worker claims and runs."""

import logging
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.agents.ingest import IngestError
from app.agents.llm import LLMError
from app.core import clock
from app.core.config import get_settings
from app.models import Job
from app.models.base import new_id

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
ACTIVE = ("queued", "running")
GENERIC_ERROR = "Something went wrong while processing this. Please try again."


class UserFacingError(Exception):
    """A failure whose message is safe and useful to show faculty."""


def enqueue(db: Session, type_: str, *, user_id: str, course_id: str | None = None,
            upload_id: str | None = None, enrollment_id: str | None = None, params: dict | None = None,
            dedupe_on: tuple[str, ...] = ACTIVE) -> Job:
    """Queue a job. If the same job is already waiting or running, return that one instead, so a
    double click (or a retry) cannot start duplicate model work. `dedupe_on` narrows which states
    count: plan jobs only merge with a queued one, because a running one has already read old data."""
    existing = db.scalar(
        select(Job).where(Job.type == type_, Job.course_id == course_id, Job.upload_id == upload_id,
                          Job.enrollment_id == enrollment_id, Job.status.in_(dedupe_on))
    )
    if existing:
        return existing
    job = Job(id=new_id(), type=type_, created_by=user_id, course_id=course_id, upload_id=upload_id,
              enrollment_id=enrollment_id, params=params or {}, progress={}, status="queued",
              created_at=clock.now())
    db.add(job)
    db.commit()
    return job


def claim_next(db: Session) -> Job | None:
    """Take the oldest queued job. SKIP LOCKED lets several workers run without taking the same one."""
    job = db.scalar(
        select(Job).where(Job.status == "queued").order_by(Job.created_at).limit(1).with_for_update(skip_locked=True)
    )
    if job is None:
        return None
    job.status, job.started_at, job.heartbeat_at = "running", clock.now(), clock.now()
    job.attempts += 1
    db.commit()
    return job


def requeue_stale(db: Session) -> int:
    """A worker that died mid-job leaves it 'running'. After a quiet period, retry it (a few times)."""
    cutoff = clock.now() - timedelta(minutes=get_settings().job_stale_minutes)
    stale = db.scalars(select(Job).where(Job.status == "running", Job.heartbeat_at < cutoff)).all()
    for j in stale:
        if j.attempts >= MAX_ATTEMPTS:
            j.status, j.finished_at = "failed", clock.now()
            j.error = "The worker stopped while processing this job. Please try again."
        else:
            j.status = "queued"
    db.commit()
    return len(stale)


def set_progress(db: Session, job: Job, step: str, done: int | None = None, total: int | None = None) -> None:
    job.progress = {"step": step, **({"done": done} if done is not None else {}),
                    **({"total": total} if total is not None else {})}
    job.heartbeat_at = clock.now()
    db.commit()


Handler = Callable[[Session, Job], dict]


def run_job(db: Session, job: Job, handlers: dict[str, Handler]) -> Job:
    """Run one claimed job to completion. Never raises: failures are recorded on the job."""
    try:
        job.result = handlers[job.type](db, job)
        job.status, job.error = "succeeded", None
        job.progress = {**(job.progress or {}), "step": "Done"}
    except (UserFacingError, IngestError, LLMError) as e:
        db.rollback()
        job = db.get(Job, job.id)
        job.status, job.error = "failed", str(e)
        log.warning("job %s failed: %s", job.id, e)
    except Exception:  # noqa: BLE001 - never leak internals to the user
        db.rollback()
        job = db.get(Job, job.id)
        job.status, job.error = "failed", GENERIC_ERROR
        log.exception("job %s crashed", job.id)
    job.finished_at = clock.now()
    db.commit()
    return job


def reset_stuck(db: Session) -> None:
    """Used on worker start: jobs left 'running' by a previous process become queued again."""
    db.execute(update(Job).where(Job.status == "running").values(status="queued"))
    db.commit()
