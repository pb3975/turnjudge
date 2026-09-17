import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CLI = [str(ROOT / ".venv" / "bin" / "python"), "-m", "turnjudge.cli"]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    d = tmp_path / "state"
    monkeypatch.setenv("TURNJUDGE_STATE_DIR", str(d))
    return d


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.email", "test@example.com")
    git(r, "config", "user.name", "Test")
    (r / "app.py").write_text("def main():\n    return 1\n")
    (r / ".gitignore").write_text("*.log\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "init")
    return r


def run_cli(args, payload=None, env=None, cwd=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run(CLI + list(args), input=json.dumps(payload) if payload is not None else "",
                       capture_output=True, text=True, env=e, cwd=cwd)
    return p


def fake_answers(**over):
    """A full answer set that passes policy, with overrides like swallows_failure=0.9 or maintenance_risk=(2.5, 0.8)."""
    ans = {}
    for q in ["unnecessary_complexity", "swallows_failure", "unrequested_behavior_change", "introduces_secret",
              "unsafe_input_use", "weakens_check", "new_external_surface"]:
        ans[q] = {"type": "noul", "noul": 0.05}
    ans["tests_proportional"] = {"type": "noul", "noul": 0.9}
    for q, top in [("behavior_added", 3), ("control_flow_added", 3), ("abstraction_added", 3),
                   ("maintenance_risk", 3), ("verbosity", 2)]:
        ans[q] = {"type": "score", "score": 0.5, "confidence": 0.9, "probabilities": {"0": 0.5, "1": 0.5},
                  "legend": {str(i): f"level {i}" for i in range(top + 1)}}
    for k, v in over.items():
        if isinstance(v, tuple):
            ans[k] = {**ans[k], "score": v[0], "confidence": v[1]}
        elif "score" in ans[k]:
            ans[k] = {**ans[k], "score": v}
        else:
            ans[k] = {"type": "noul", "noul": v}
    return ans


def write_fake(path: Path, default=None, by_path=None) -> str:
    path.write_text(json.dumps({"default": default or fake_answers(), "by_path": by_path or {}}))
    return str(path)
