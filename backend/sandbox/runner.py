#!/usr/bin/env python3
"""Compile and run one submission against its tests. Runs INSIDE the sandbox container.

    runner.py --payload /payload.json

The payload is read and deleted before any student code runs, so it never sits on disk where the
code could read it (the hidden tests are in it). Student code runs as an unprivileged user with
resource limits; the container itself has no network and a small memory/process budget.

The only thing printed on stdout is one line:  @@RESULT@@ {json}
Student output never reaches this process's stdout: it is captured to files and truncated.

Only the standard library is used, so the image stays small and this file is easy to audit.
"""

import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time

MARK = "@@RESULT@@"
NOBODY = 65534
MAX_OUT = 1 << 20          # bytes a program may write to stdout
SHOW = 2000                # characters of output kept in the report
COMPILE_SECONDS = 20
COMPILE_SHOW = 4000

LANGS = {
    "c": {"file": "main.c", "compile": ["gcc", "-O2", "-std=c17", "-o", "main", "main.c", "-lm"], "run": ["./main"]},
    "cpp": {"file": "main.cpp", "compile": ["g++", "-O2", "-std=c++17", "-o", "main", "main.cpp"], "run": ["./main"]},
    "python": {"file": "main.py", "compile": None, "run": [sys.executable or "python3", "main.py"]},
}


def emit(result: dict) -> None:
    sys.stdout.write("\n" + MARK + " " + json.dumps(result) + "\n")
    sys.stdout.flush()


def drop() -> dict:
    """Popen arguments that run a child as the unprivileged user (only possible, and only needed, as root)."""
    return {"user": NOBODY, "group": NOBODY, "extra_groups": []} if os.geteuid() == 0 else {}


def limits(cpu_seconds: int, fsize: int):
    def apply():
        os.setsid()
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        if os.geteuid() == 0:  # per-user count, and the student user has no other processes
            resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))

    return apply


def clean(text: str) -> str:
    """Compare ignoring line-ending style, trailing spaces and trailing blank lines."""
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).rstrip("\n")


def kill_group(p: subprocess.Popen) -> None:
    try:
        os.killpg(p.pid, 9)
    except ProcessLookupError:
        pass


def env(work: str) -> dict:
    return {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": work, "TMPDIR": work, "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}


def compile_source(lang: dict, work: str) -> str | None:
    """Returns the compiler's complaint, or None on success."""
    if not lang["compile"]:
        return None
    p = subprocess.Popen(lang["compile"], cwd=work, env=env(work), stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
                         preexec_fn=limits(COMPILE_SECONDS, 16 << 20), **drop())
    try:
        out, _ = p.communicate(timeout=COMPILE_SECONDS + 5)
    except subprocess.TimeoutExpired:
        kill_group(p)
        return "The compiler took too long."
    return None if p.returncode == 0 else (out or "Compilation failed.")[:COMPILE_SHOW]


def run_test(lang: dict, work: str, stdin_text: str, expected: str, limit_ms: int, outdir: str, n: int) -> dict:
    out_path, err_path = os.path.join(outdir, f"{n}.out"), os.path.join(outdir, f"{n}.err")
    cpu = max(1, -(-limit_ms // 1000)) + 1
    start = time.perf_counter()
    verdict, code = "ok", 0
    with open(out_path, "wb") as fo, open(err_path, "wb") as fe:
        p = subprocess.Popen(lang["run"], cwd=work, env=env(work), stdin=subprocess.PIPE, stdout=fo, stderr=fe,
                             preexec_fn=limits(cpu, MAX_OUT), **drop())
        try:
            p.communicate(stdin_text.encode(), timeout=limit_ms / 1000)
            code = p.returncode
        except subprocess.TimeoutExpired:
            kill_group(p)
            p.communicate()
            verdict = "time_limit"
        except BrokenPipeError:  # the program exited without reading its input
            code = p.wait()
        kill_group(p)  # anything it left behind
    ms = round((time.perf_counter() - start) * 1000)
    out = open(out_path, "rb").read(MAX_OUT + 1).decode("utf-8", "replace")
    err = open(err_path, "rb").read(SHOW).decode("utf-8", "replace")
    if verdict == "ok":
        if len(out.encode()) > MAX_OUT or code in (-25, 153):  # SIGXFSZ
            verdict = "output_limit"
        elif code == -24 or code == -9 and ms >= limit_ms:   # SIGXCPU / killed at the limit
            verdict = "time_limit"
        elif code != 0:
            verdict = "runtime_error"
        elif clean(out) != clean(expected):
            verdict = "wrong_answer"
    return {"verdict": verdict, "ms": ms, "exit": code, "stdout": out[:SHOW], "stderr": err}


def main() -> None:
    path = sys.argv[sys.argv.index("--payload") + 1]
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    os.remove(path)  # before any student code runs

    lang = LANGS.get(payload["language"])
    if lang is None:
        return emit({"status": "error", "message": "unsupported language"})
    base = os.environ.get("RUNNER_WORKDIR") or "/sandbox"
    os.makedirs(base, exist_ok=True)
    work = tempfile.mkdtemp(prefix="w", dir=base)
    outdir = tempfile.mkdtemp(prefix="o", dir=base)
    try:
        os.chmod(outdir, 0o700)
        os.chmod(work, 0o755)
        src = os.path.join(work, lang["file"])
        with open(src, "w", encoding="utf-8") as f:
            f.write(payload["source"])
        os.chmod(src, 0o644)
        if os.geteuid() == 0:
            shutil.chown(work, NOBODY, NOBODY)  # the compiler writes the binary here as the student user
        complaint = compile_source(lang, work)
        if complaint is not None:
            return emit({"status": "compile_error", "compile_output": complaint, "tests": []})
        results, stop = [], False
        for n, t in enumerate(payload["tests"]):
            if stop:
                results.append({"verdict": "skipped", "ms": 0, "exit": 0, "stdout": "", "stderr": ""})
                continue
            r = run_test(lang, work, t["input"], t["expected"], int(payload["time_limit_ms"]), outdir, n)
            results.append(r)
            stop = r["verdict"] == "time_limit"  # later tests would only wait for the same loop
        emit({"status": "ok", "compile_output": "", "tests": results})
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(outdir, ignore_errors=True)


if __name__ == "__main__":
    main()
