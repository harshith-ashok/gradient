"""Background worker: `python -m app.worker`. Runs one job at a time (one model server, one GPU)."""

import logging
import signal
import time

from app.core.db import session_factory
from app.services import jobs
from app.services.pipeline import HANDLERS

log = logging.getLogger("worker")
_stop = False


def _handle_signal(*_):
    global _stop
    _stop = True
    log.info("stopping after the current job")


def run_once() -> bool:
    """Claim and run one job. Returns False when the queue is empty."""
    with session_factory()() as db:
        jobs.requeue_stale(db)
        job = jobs.claim_next(db)
        if job is None:
            return False
        log.info("running %s job %s", job.type, job.id)
        jobs.run_job(db, job, HANDLERS)
        return True


def main(poll_seconds: float = 1.0) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    with session_factory()() as db:
        jobs.reset_stuck(db)  # a previous worker may have died mid-job
    log.info("worker started")
    while not _stop:
        if not run_once():
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
