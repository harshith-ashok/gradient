"""The code judge: `python -m app.judge`. Runs student submissions in throwaway Docker containers."""

import logging
import signal
import threading
import time

from app.core.config import get_settings
from app.core.db import session_factory
from app.core.observability import configure_logging
from app.services import judge

log = logging.getLogger("judge")
_stop = threading.Event()


def loop(n: int) -> None:
    while not _stop.is_set():
        try:
            with session_factory()() as db:
                sub = judge.claim_next(db)
                if sub is not None:
                    log.info("worker %d judging %s (%s, %s)", n, sub.id, sub.language, sub.mode)
                    judge.process(db, sub)
                    continue
        except Exception:  # noqa: BLE001 - one bad submission must not stop the judge
            log.exception("judge loop error")
        judge.cache_heartbeat()
        _stop.wait(0.5)


def main() -> None:
    s = get_settings()
    s.log_source = "judge"
    configure_logging(s.log_json)
    signal.signal(signal.SIGTERM, lambda *_: _stop.set())
    signal.signal(signal.SIGINT, lambda *_: _stop.set())
    while not _stop.is_set():
        try:
            judge.get_backend()  # fail early and visibly if Docker or the image is missing
            break
        except judge.JudgeUnavailable as e:
            log.error("%s. Retrying in 10 s.", e)
            _stop.wait(10)
    with session_factory()() as db:
        judge.fail_stale(db)
    log.info("judge started with %s backend, %d at a time", s.judge_backend, s.judge_concurrency)
    threads = [threading.Thread(target=loop, args=(i,), daemon=True) for i in range(s.judge_concurrency)]
    for t in threads:
        t.start()
    while not _stop.is_set():
        time.sleep(1)
    for t in threads:
        t.join(timeout=5)


if __name__ == "__main__":
    main()
