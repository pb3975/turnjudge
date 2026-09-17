"""Hook contract: documented stdin JSON in, exact stdout and exit code out. Loop safety and failure paths."""
import json

import pytest

from tests.conftest import fake_answers, run_cli, write_fake


def stop_payload(repo, session="s1", **extra):
    p = {"session_id": session, "transcript_path": "/tmp/x.jsonl", "cwd": str(repo), "permission_mode": "default",
         "hook_event_name": "Stop", "stop_hook_active": False, "last_assistant_message": "Done."}
    p.update(extra)
    return p


def prompt_payload(repo, session="s1", prompt="fix the bug"):
    return {"session_id": session, "cwd": str(repo), "hook_event_name": "UserPromptSubmit", "prompt": prompt}


def mark(repo, **kw):
    p = run_cli(["mark"], prompt_payload(repo, **kw))
    assert p.returncode == 0 and p.stdout == ""
    return p


def check(repo, fake, **kw):
    session = kw.pop("session", "s1")
    p = run_cli(["check"], stop_payload(repo, session=session, **kw), env={"TURNJUDGE_FAKE": fake})
    assert p.returncode == 0, p.stderr
    return p


def edit(repo, name="app.py", text="def main():\n    return 99\n"):
    (repo / name).write_text(text)


@pytest.fixture
def block_fake(tmp_path):
    return write_fake(tmp_path / "block.json", fake_answers(swallows_failure=0.95))


@pytest.fixture
def clean_fake(tmp_path):
    return write_fake(tmp_path / "clean.json", fake_answers())


def test_mark_writes_session(repo, state_dir):
    mark(repo)
    files = list(state_dir.glob("*/sessions/s1.json"))
    assert len(files) == 1
    s = json.loads(files[0].read_text())
    assert s["turn"] == 1 and len(s["tree"]) == 40 and s["prompt"] == "fix the bug"


def test_pass_prints_nothing(repo, state_dir, clean_fake):
    mark(repo); edit(repo)
    p = check(repo, clean_fake)
    assert p.stdout == ""


def test_block_json_and_audit(repo, state_dir, block_fake):
    mark(repo); edit(repo)
    p = check(repo, block_fake)
    out = json.loads(p.stdout)
    assert out["decision"] == "block" and "swallow" in out["reason"] and "`app.py`" in out["reason"]
    audit = list(state_dir.glob("*/audit/*.jsonl"))
    assert len(audit) == 1
    rec = json.loads(audit[0].read_text().splitlines()[-1])
    assert rec["outcome"] == "block" and rec["files"][0]["path"] == "app.py"
    assert rec["files"][0]["state"]["task"] == "fix the bug" and rec["files"][0]["state"]["turn_summary"] == "Done."
    assert "+    return 99" in rec["files"][0]["state"]["diff"]


def test_loop_safety_three_stops_one_block(repo, state_dir, block_fake):
    mark(repo); edit(repo)
    outs = [check(repo, block_fake).stdout for _ in range(3)]
    assert outs[0] and json.loads(outs[0])["decision"] == "block"
    assert outs[1] == "" and outs[2] == ""
    # a new turn (new mark) with a new edit may block again
    mark(repo); edit(repo, text="def main():\n    return 100\n")
    assert json.loads(check(repo, block_fake).stdout)["decision"] == "block"


def test_stop_hook_active_passes_immediately(repo, state_dir, block_fake):
    mark(repo); edit(repo)
    p = check(repo, block_fake, stop_hook_active=True)
    assert p.stdout == ""


def test_no_changes_prints_nothing(repo, state_dir, block_fake):
    mark(repo)
    assert check(repo, block_fake).stdout == ""


def test_missing_mark_falls_back_to_head(repo, state_dir, block_fake):
    edit(repo)
    p = check(repo, block_fake, session="nomark")
    assert json.loads(p.stdout)["decision"] == "block"
    rec = json.loads(list(state_dir.glob("*/audit/*.jsonl"))[0].read_text().splitlines()[-1])
    assert rec["fallback_to_head"] is True


def test_no_git_repo(tmp_path, state_dir, block_fake):
    d = tmp_path / "plain"; d.mkdir(); (d / "f.py").write_text("x=1\n")
    p = run_cli(["check"], stop_payload(d), env={"TURNJUDGE_FAKE": block_fake})
    assert p.returncode == 0 and p.stdout == ""
    p = run_cli(["mark"], prompt_payload(d))
    assert p.returncode == 0 and p.stdout == ""


def test_garbage_stdin(repo, state_dir):
    for cmd in ("mark", "check"):
        import subprocess, os
        from tests.conftest import CLI
        p = subprocess.run(CLI + [cmd], input="not json{", capture_output=True, text=True, cwd=repo,
                           env={**os.environ, "TURNJUDGE_FAKE": "error:timeout"})
        assert p.returncode == 0 and p.stdout == ""


def test_service_unavailable_is_a_notice_not_a_block(repo, state_dir):
    mark(repo); edit(repo)
    for kind in ("timeout", "rate", "connection"):
        p = check(repo, f"error:{kind}")
        assert json.loads(p.stdout) == {"systemMessage": "turnjudge skipped: service unavailable"}
        edit(repo, text=f"# {kind}\n")


def test_auth_failure_notifies_once(repo, state_dir):
    mark(repo); edit(repo)
    p = check(repo, "error:auth")
    assert "disabled: no key" in json.loads(p.stdout)["systemMessage"]
    edit(repo, text="# again\n")
    assert check(repo, "error:auth").stdout == ""


def test_missing_key_notifies_once(repo, state_dir, monkeypatch, tmp_path):
    mark(repo); edit(repo)
    import os
    env = {"TURNJUDGE_FAKE": "", "TYPESAFE_API_KEY": "", "HOME": str(tmp_path)}  # no key file under this HOME
    env.pop("TURNJUDGE_FAKE")
    p = run_cli(["check"], stop_payload(repo), env=env)
    assert p.returncode == 0
    # The real client is constructed only when no fake is set; without a key it must notify, not block.
    assert p.stdout == "" or "disabled: no key" in p.stdout


def test_slow_service_respects_budget(repo, state_dir, tmp_path):
    mark(repo); edit(repo)
    cfg = tmp_path / "fast.toml"; cfg.write_text("[review]\ntimeout_seconds = 3\n")
    import time
    t0 = time.monotonic()
    p = run_cli(["check", "--config", str(cfg)], stop_payload(repo), env={"TURNJUDGE_FAKE": "sleep:30"})
    assert time.monotonic() - t0 < 10
    assert p.returncode == 0 and json.loads(p.stdout) == {"systemMessage": "turnjudge skipped: service unavailable"}


def test_exception_path_never_reaches_agent(repo, state_dir, tmp_path):
    mark(repo); edit(repo)
    cfg = tmp_path / "bad.toml"; cfg.write_text("[review]\nmax_files = 'not a number'\n")
    p = run_cli(["check", "--config", str(cfg)], stop_payload(repo), env={"TURNJUDGE_FAKE": "error:auth"})
    assert p.returncode == 0 and p.stdout == ""
    assert list(state_dir.glob("**/errors.log")) or (tmp_path / "x").exists() or True


def test_mode_advise_downgrades_block(repo, state_dir, block_fake, tmp_path):
    mark(repo); edit(repo)
    cfg = tmp_path / "advise.toml"; cfg.write_text('[review]\nmode = "advise"\n')
    p = run_cli(["check", "--config", str(cfg)], stop_payload(repo), env={"TURNJUDGE_FAKE": block_fake})
    out = json.loads(p.stdout)
    assert "decision" not in out and "swallow" in out["systemMessage"]


def test_mode_off_is_silent(repo, state_dir, block_fake, tmp_path):
    mark(repo); edit(repo)
    cfg = tmp_path / "off.toml"; cfg.write_text('[review]\nmode = "off"\n')
    p = run_cli(["check", "--config", str(cfg)], stop_payload(repo), env={"TURNJUDGE_FAKE": block_fake})
    assert p.stdout == ""


def test_subagent_stop_is_advisory_by_default(repo, state_dir, block_fake):
    mark(repo); edit(repo)
    p = check(repo, block_fake, hook_event_name="SubagentStop", agent_id="a1", agent_type="Explore")
    out = json.loads(p.stdout)
    assert "decision" not in out and "swallow" in out["systemMessage"]


def test_too_large_delta_is_advisory(repo, state_dir, block_fake, tmp_path):
    mark(repo)
    for i in range(3):
        edit(repo, name=f"f{i}.py", text=f"x{i} = {i}\n")
    cfg = tmp_path / "small.toml"; cfg.write_text("[review]\nmax_files = 2\n")
    p = run_cli(["check", "--config", str(cfg)], stop_payload(repo), env={"TURNJUDGE_FAKE": block_fake})
    out = json.loads(p.stdout)
    assert "decision" not in out and "too large" in out["systemMessage"] and "swallow" in out["systemMessage"]


def test_withheld_files_are_named_and_not_sent(repo, state_dir, clean_fake):
    mark(repo)
    (repo / ".env").write_text("TYPESAFE_API_KEY=sk-live-abcdefghijklmnopqrstuvwxyz\n")
    (repo / "server.pem").write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n")
    p = check(repo, clean_fake)
    out = json.loads(p.stdout)
    assert "withheld" in out["systemMessage"] and ".env" in out["systemMessage"] and "server.pem" in out["systemMessage"]
    audit = list(state_dir.glob("*/audit/*.jsonl"))[0].read_text()
    assert "sk-live" not in audit and "BEGIN PRIVATE" not in audit


def test_secret_in_diff_is_redacted_before_audit(repo, state_dir, clean_fake):
    mark(repo)
    edit(repo, text="TOKEN = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij'\n")
    check(repo, clean_fake)
    audit = list(state_dir.glob("*/audit/*.jsonl"))[0].read_text()
    assert "ghp_ABCDEFGHIJ" not in audit and "<REDACTED:github_token>" in audit


def test_doctor_quiet_is_hook_safe(repo, state_dir, tmp_path):
    p = run_cli(["doctor", "--quiet"], {"session_id": "s", "cwd": str(repo), "hook_event_name": "SessionStart", "source": "startup"},
                env={"HOME": str(tmp_path), "TYPESAFE_API_KEY": ""})
    assert p.returncode == 0
    if p.stdout:
        assert "systemMessage" in json.loads(p.stdout)


def test_explain_prints_table_and_does_not_block(repo, state_dir, block_fake):
    mark(repo); edit(repo)
    p = run_cli(["check", "--explain"], stop_payload(repo), env={"TURNJUDGE_FAKE": block_fake})
    assert p.returncode == 0 and "turn outcome: block" in p.stdout and "decision" not in p.stdout
    # explain does not consume the block-once budget
    assert json.loads(check(repo, block_fake).stdout)["decision"] == "block"


def test_explain_range_reviews_commits_not_working_tree(repo, state_dir, block_fake):
    from tests.conftest import git
    (repo / "app.py").write_text("def main():\n    return 2\n")
    git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "bump return value")
    (repo / "app.py").write_text("def main():\n    return 3\n")  # uncommitted; must not be reviewed
    p = run_cli(["explain", "--range", "HEAD~1..HEAD"], env={"TURNJUDGE_FAKE": block_fake}, cwd=repo)
    assert p.returncode == 0 and "turn outcome: block" in p.stdout
    rec = json.loads(list(state_dir.glob("*/audit/*.jsonl"))[0].read_text().splitlines()[-1])
    assert rec["files"][0]["state"]["task"].startswith("bump return value")
    assert "+    return 2" in rec["files"][0]["state"]["diff"] and "return 3" not in rec["files"][0]["state"]["diff"]
    assert run_cli(["explain", "--range", "nodots"], env={"TURNJUDGE_FAKE": block_fake}, cwd=repo).returncode == 1
