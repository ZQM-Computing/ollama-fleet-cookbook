"""Mock-based tests for scripts/fleet_health.sh exit-code logic.

The script itself needs a live Ollama fleet to mean anything, so these
tests do not claim to test a real fleet. They test exactly what can be
tested offline: given hosts that answer / do not answer, does the script
exit 0 / nonzero, and does it report DOWN hosts? ``curl`` and ``jq`` are
replaced with small fakes on PATH, so no network and no real jq are used.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "scripts" / "fleet_health.sh"

FAKE_CURL = '''#!/usr/bin/env python3
"""Fake curl for fleet_health tests: answers for up hosts, silence for down hosts."""
import json
import sys

url = [a for a in sys.argv[1:] if a.startswith("http://")][-1]
host = url.split("/")[2]
if "down" in host:
    sys.exit(22)
if url.endswith("/api/tags"):
    print(json.dumps({"models": [{"name": "llama3.1:8b"}, {"name": "qwen2.5:14b"}]}))
elif url.endswith("/api/ps"):
    print(json.dumps({"models": [{"name": "llama3.1:8b"}]}))
else:
    sys.exit(22)
'''

FAKE_JQ = '''#!/usr/bin/env python3
"""Fake jq for fleet_health tests: handles only the two queries the script uses."""
import json
import sys

data = json.load(sys.stdin)
args = " ".join(sys.argv[1:])
if "length" in args:
    print(len(data["models"]))
else:
    print(", ".join(m["name"] for m in data["models"]))
'''


def _run_script(tmp_path, *hosts):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name, body in (("curl", FAKE_CURL), ("jq", FAKE_JQ)):
        exe = bindir / name
        exe.write_text(body)
        exe.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    return subprocess.run(
        ["bash", str(SCRIPT), *hosts],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def test_script_exists():
    assert SCRIPT.is_file(), "scripts/fleet_health.sh is missing"


def test_all_hosts_up_exits_zero(tmp_path):
    result = _run_script(tmp_path, "up-host:11434", "up-host-2:11434")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "up" in result.stdout
    assert "models installed: 2" in result.stdout


def test_one_host_down_exits_nonzero_and_reports_down(tmp_path):
    result = _run_script(tmp_path, "up-host:11434", "down-host:11434")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "DOWN" in result.stdout
    assert "down-host:11434" in result.stdout


def test_no_args_uses_default_localhost(tmp_path):
    # With no hosts given, the script defaults to localhost:11434, which
    # our fake curl treats as an up host (it contains no "down").
    result = _run_script(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "localhost:11434" in result.stdout


if __name__ == "__main__":
    sys.exit("run with pytest")
