"""Offline integration: the full check path against recorded Jev responses from calibration."""
import json
from pathlib import Path

from jev_review.policy import Answers, decide_file
from tests.conftest import run_cli

RESP = Path(__file__).resolve().parent.parent / "calibration" / "responses"


def test_recorded_responses_drive_policy_offline():
    files = sorted(p for p in RESP.glob("*.json") if p.name != "latency.json")
    assert len(files) >= 20
    outcomes = {}
    for f in files:
        rec = json.loads(f.read_text())
        assert rec["response"] and "answers" in rec["response"]
        v = decide_file(rec["file"], Answers(rec["response"]), task=rec["state"]["task"])
        outcomes[f.name] = v.outcome
        assert set(v.values) >= {"swallows_failure", "behavior_added", "maintenance_risk_conf"}
    assert "block" in outcomes.values() and "pass" in outcomes.values()


def test_full_check_with_recorded_fixture(repo, state_dir, tmp_path):
    rec = json.loads((RESP / "57a64d12ec-src_agentlab_tools.py.json").read_text())
    fake = tmp_path / "fx.json"
    fake.write_text(json.dumps({"default": rec["response"]["answers"]}))
    run_cli(["mark"], {"session_id": "fx", "cwd": str(repo), "prompt": "Add local Ollama provider support"})
    (repo / "app.py").write_text("def write_file(path, lines):\n    return lines\n")
    p = run_cli(["check"], {"session_id": "fx", "cwd": str(repo), "hook_event_name": "Stop", "stop_hook_active": False,
                            "last_assistant_message": "Added the provider."}, env={"JEV_REVIEW_FAKE": str(fake)})
    out = json.loads(p.stdout)
    assert out["decision"] == "block" and "task did not ask for" in out["reason"]
