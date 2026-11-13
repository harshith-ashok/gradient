"""Run a student's code against a problem's tests, inside a sandbox.

Two backends run the same `sandbox/runner.py`:

  docker  a fresh container per submission: no network, memory/CPU/process limits, all capabilities dropped
          except the few the runner needs to switch to an unprivileged user and stop it; student code runs as that user,
          nothing is kept afterwards. This is the real thing.
  local   a plain subprocess. No isolation at all: only for the automated tests, refused outside ENV=dev.

The judge process (`python -m app.judge`) claims queued submissions from Postgres, so a slow compile never
blocks the API and a crash loses nothing: unfinished submissions are failed, not re-run forever.
"""

import io
import json
import logging
import subprocess
import sys
import tarfile
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import cache, clock
from app.core.config import get_settings
from app.models import CodeSubmission, CodingProblem

log = logging.getLogger(__name__)
RUNNER = Path(__file__).resolve().parents[2] / "sandbox" / "runner.py"
MARK = "@@RESULT@@"
HEARTBEAT_KEY = "judge:heartbeat"
STALE_AFTER = timedelta(minutes=5)
SHOW = 2000


class JudgeUnavailable(Exception):
    """The sandbox cannot be used (no Docker, image missing). Shown to students as 'try again later'."""


class Backend(Protocol):
    def run(self, payload: dict, timeout: float) -> dict: ...


def _parse(text: str) -> dict | None:
    for line in reversed(text.splitlines()):
        if line.startswith(MARK):
            try:
                return json.loads(line[len(MARK):])
            except ValueError:
                return None
    return None


class LocalBackend:
    def __init__(self) -> None:
        if get_settings().env != "dev":
            raise JudgeUnavailable("The local judge runs code without isolation and is only allowed in dev.")

    def run(self, payload: dict, timeout: float) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.json"
            path.write_text(json.dumps(payload))
            try:
                env = {"RUNNER_WORKDIR": str(Path(tmp) / "work"), "PATH": "/usr/local/bin:/usr/bin:/bin"}
                p = subprocess.run([sys.executable, str(RUNNER), "--payload", str(path)], capture_output=True,
                                   text=True, timeout=timeout, env=env)
            except subprocess.TimeoutExpired:
                return {"status": "crashed"}
        return _parse(p.stdout) or {"status": "crashed"}


class DockerBackend:
    def __init__(self) -> None:
        try:
            import docker

            self.client = docker.from_env()
            self.client.ping()
        except Exception as e:  # noqa: BLE001
            raise JudgeUnavailable(f"Docker is not reachable: {e}") from e
        self._cleanup_leftovers()

    def _cleanup_leftovers(self) -> None:
        for c in self.client.containers.list(all=True, filters={"label": "gradient.sandbox=1"}):
            c.remove(force=True)

    def run(self, payload: dict, timeout: float) -> dict:
        s = get_settings()
        memory = f"{int(payload['memory_mb']) + 192}m"  # the student's budget plus the compiler and runner
        raw = json.dumps(payload).encode()
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            info = tarfile.TarInfo("payload.json")
            info.size, info.mode = len(raw), 0o600
            tar.addfile(info, io.BytesIO(raw))
        buf.seek(0)
        container = None
        try:
            container = self.client.containers.create(
                s.sandbox_image, command=["--payload", "/payload.json"], user="0", detach=True,
                network_mode="none", mem_limit=memory, memswap_limit=memory, nano_cpus=1_000_000_000,
                pids_limit=128, cap_drop=["ALL"], cap_add=["SETUID", "SETGID", "CHOWN", "KILL"],
                security_opt=["no-new-privileges"],
                tmpfs={"/sandbox": "rw,exec,nosuid,nodev,size=64m", "/tmp": "rw,noexec,nosuid,nodev,size=16m"},
                labels={"gradient.sandbox": "1"}, runtime=s.sandbox_runtime or None,
            )
            container.put_archive("/", buf.getvalue())
            container.start()
            try:
                container.wait(timeout=timeout)
            except Exception:  # noqa: BLE001 - a timeout in the client; stop the container
                container.kill()
                return {"status": "crashed"}
            logs = container.logs(stdout=True, stderr=False, tail=50).decode("utf-8", "replace")
            return _parse(logs) or {"status": "crashed"}
        except JudgeUnavailable:
            raise
        except Exception as e:  # noqa: BLE001 - image missing, daemon gone, and so on
            raise JudgeUnavailable(f"The sandbox could not start: {e}") from e
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:  # noqa: BLE001
                    log.warning("could not remove sandbox container", exc_info=True)


_backend: Backend | None = None


def get_backend() -> Backend:
    global _backend
    if _backend is None:
        _backend = LocalBackend() if get_settings().judge_backend == "local" else DockerBackend()
    return _backend


def set_backend(b: Backend | None) -> None:
    global _backend
    _backend = b


# ------------------------------------------------------------------ judging


def tests_for(problem: CodingProblem, mode: str) -> list[tuple[int, dict]]:
    tests = list(enumerate(problem.tests))
    return [(i, t) for i, t in tests if t.get("sample")] if mode == "run" else tests


def judge(sub: CodeSubmission, problem: CodingProblem, backend: Backend) -> None:
    """Fill in the verdict, counts and per-test results on `sub`."""
    chosen = tests_for(problem, sub.mode)
    payload = {
        "language": sub.language, "source": sub.code, "time_limit_ms": problem.time_limit_ms,
        "memory_mb": problem.memory_mb,
        "tests": [{"input": t["input"], "expected": t["expected"]} for _, t in chosen],
    }
    budget = 30 + len(chosen) * (problem.time_limit_ms / 1000 + 1)
    sub.total = len(chosen)
    out = backend.run(payload, budget)

    if out.get("status") == "compile_error":
        sub.verdict, sub.compile_output, sub.results = "compile_error", out.get("compile_output", ""), []
        return
    if out.get("status") != "ok":
        sub.verdict = "runtime_error" if out.get("status") == "crashed" else "internal_error"
        sub.message = ("The sandbox stopped unexpectedly. The program may have used too much memory or time."
                       if out.get("status") == "crashed" else out.get("message", "The runner failed.")[:300])
        return

    full = sub.mode == "check"
    results, first_bad, slowest = [], None, 0
    for (index, test), r in zip(chosen, out["tests"], strict=False):
        sample = bool(test.get("sample"))
        row = {"index": index, "sample": sample, "verdict": r["verdict"], "ms": r["ms"]}
        if sample or full:  # hidden tests never reveal their data to students
            row |= {"input": test["input"][:SHOW], "expected": test["expected"][:SHOW],
                    "stdout": r["stdout"], "stderr": r["stderr"]}
        results.append(row)
        if r["verdict"] == "ok":
            sub.passed += 1
            slowest = max(slowest, r["ms"])
        elif first_bad is None and r["verdict"] != "skipped":
            first_bad = r["verdict"]
    sub.results = results
    sub.runtime_ms = slowest or None
    sub.verdict = "accepted" if sub.passed == sub.total else (first_bad or "wrong_answer")


def claim_next(db: Session) -> CodeSubmission | None:
    sub = db.scalar(select(CodeSubmission).where(CodeSubmission.state == "queued")
                    .order_by(CodeSubmission.created_at).limit(1).with_for_update(skip_locked=True))
    if sub is None:
        return None
    sub.state, sub.started_at = "running", clock.now()
    db.commit()
    return sub


def process(db: Session, sub: CodeSubmission, backend: Backend | None = None) -> None:
    problem = db.get(CodingProblem, sub.problem_id)
    try:
        if problem is None:
            sub.verdict, sub.message = "internal_error", "This problem no longer exists."
        else:
            judge(sub, problem, backend or get_backend())
    except JudgeUnavailable as e:
        log.error("sandbox unavailable: %s", e)
        sub.verdict = "internal_error"
        sub.message = "The code runner is unavailable right now. Please try again in a few minutes."
    except Exception:  # noqa: BLE001
        log.exception("judging %s crashed", sub.id)
        sub.verdict, sub.message = "internal_error", "Something went wrong while running your code."
    sub.state, sub.finished_at = "done", clock.now()
    db.commit()
    cache_heartbeat()


def process_pending(db: Session, backend: Backend | None = None, limit: int = 100) -> int:
    n = 0
    while n < limit and (sub := claim_next(db)) is not None:
        process(db, sub, backend)
        n += 1
    return n


def fail_stale(db: Session) -> int:
    """A judge that died mid-run leaves 'running' rows. Fail them rather than re-running student code forever."""
    stale = db.scalars(select(CodeSubmission).where(CodeSubmission.state == "running",
                                                    CodeSubmission.started_at < clock.now() - STALE_AFTER)).all()
    for s in stale:
        s.state, s.verdict, s.finished_at = "done", "internal_error", clock.now()
        s.message = "The code runner stopped while running this. Please submit again."
    db.commit()
    return len(stale)


def cache_heartbeat() -> None:
    try:
        cache._client().set(HEARTBEAT_KEY, "1", ex=30)
    except Exception:  # noqa: BLE001
        pass


def alive() -> bool:
    try:
        return cache._client().get(HEARTBEAT_KEY) is not None
    except Exception:  # noqa: BLE001
        return False
