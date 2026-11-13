"""The real sandbox. Needs Docker and the image:  docker build -t gradient-sandbox backend/sandbox
Run with:  LIVE_DOCKER=1 uv run pytest tests/test_sandbox_docker.py -s"""

import os

import pytest

from app.services.judge import DockerBackend

pytestmark = pytest.mark.skipif(not os.environ.get("LIVE_DOCKER"), reason="set LIVE_DOCKER=1 to run against Docker")


@pytest.fixture(scope="module")
def box():
    return DockerBackend()


def run(box, source, language="python", expected="", stdin="", limit=1500, memory=64, timeout=60):
    out = box.run({"language": language, "source": source, "time_limit_ms": limit, "memory_mb": memory,
                   "tests": [{"input": stdin, "expected": expected}]}, timeout)
    return out, (out["tests"][0] if out.get("tests") else None)


def test_a_normal_program_passes(box):
    _, t = run(box, "print(sum(map(int, input().split())))", stdin="2 3\n", expected="5\n")
    assert t["verdict"] == "ok"


def test_c_and_cpp_compile_and_run(box):
    c = '#include <stdio.h>\nint main(void){puts("hi");return 0;}\n'
    cpp = '#include <iostream>\nint main(){std::cout << "hi\\n";}\n'
    assert run(box, c, "c", "hi\n")[1]["verdict"] == "ok"
    assert run(box, cpp, "cpp", "hi\n")[1]["verdict"] == "ok"
    out, _ = run(box, "int main( {", "c")
    assert out["status"] == "compile_error" and "error" in out["compile_output"]


def test_student_code_runs_unprivileged(box):
    _, t = run(box, "import os\nprint(os.getuid(), os.geteuid())", expected="65534 65534\n")
    assert t["verdict"] == "ok", t


def test_there_is_no_network(box):
    code = ("import socket\ntry:\n    socket.create_connection(('1.1.1.1', 53), timeout=1)\n    print('reached')\n"
            "except OSError:\n    print('blocked')\n")
    assert run(box, code, expected="blocked\n")[1]["verdict"] == "ok"


def test_the_hidden_tests_cannot_be_read(box):
    code = ("import glob\nfound = []\n"
            "for pat in ('/payload.json', '/sandbox/*', '/tmp/*', '/proc/1/environ', '/proc/1/mem'):\n"
            "    for f in glob.glob(pat):\n        try:\n            open(f).read(); found.append(f)\n"
            "        except OSError:\n            pass\nprint(found)\n")
    _, t = run(box, code, expected="[]\n")
    assert t["verdict"] == "ok", t["stdout"]


def test_the_filesystem_cannot_be_modified(box):
    code = ("for p in ('/etc/motd', '/opt/runner/runner.py', '/usr/bin/x'):\n"
            "    try:\n        open(p, 'w').write('x')\n"
            "        print('WROTE', p)\n    except OSError:\n        pass\nprint('done')\n")
    _, t = run(box, code, expected="done\n")
    assert t["verdict"] == "ok", t["stdout"]


def test_infinite_loops_are_stopped(box):
    _, t = run(box, "while True:\n    pass\n", limit=500)
    assert t["verdict"] == "time_limit"


def test_memory_bombs_are_killed_not_the_host(box):
    out, t = run(box, "x = bytearray(2 * 1024 ** 3)\nprint('allocated')\n", memory=64)
    assert out["status"] in ("ok", "crashed")
    assert t is None or t["verdict"] in ("runtime_error", "time_limit")


def test_fork_bombs_are_contained_and_cleaned_up(box):
    out, t = run(box, "import os\nwhile True:\n    os.fork()\n", limit=1500)
    assert out["status"] in ("ok", "crashed")
    assert t is None or t["verdict"] in ("runtime_error", "time_limit")
    assert box.client.containers.list(all=True, filters={"label": "gradient.sandbox=1"}) == []


def test_huge_output_is_capped(box):
    out, t = run(box, "while True:\n    print('x' * 1000)\n", limit=1500)
    assert t["verdict"] in ("output_limit", "time_limit", "runtime_error")
    assert len(t["stdout"]) <= 2000
