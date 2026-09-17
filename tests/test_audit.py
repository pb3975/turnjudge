import json
import subprocess

import pytest

from jev_review.audit import daily_summary, run_audit
from jev_review.config import load_config
from jev_review.store import Store


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=r, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=r, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=r, check=True)
    return r


def write_audit_day(store: Store, day: str, records: list[dict]) -> None:
    p = store.audit_dir / f"{day}.jsonl"
    with p.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def test_daily_summary_counts_outcomes_and_tokens(tmp_path, monkeypatch, repo):
    monkeypatch.setenv("JEV_REVIEW_STATE_DIR", str(tmp_path / "state"))
    cfg = load_config(repo)
    store = Store(cfg, repo)
    write_audit_day(store, "2026-09-16", [
        {"outcome": "block", "usage": {"input_tokens": 100}},
        {"outcome": "advise", "usage": {"input_tokens": 50}},
        {"outcome": "pass", "usage": {"input_tokens": 10}},
        {"outcome": "skipped"},
    ])
    write_audit_day(store, "2026-09-17", [
        {"outcome": "block", "usage": {"input_tokens": 5}},
    ])

    days = daily_summary(store)

    assert days["2026-09-16"] == {"checks": 4, "blocks": 1, "advisories": 1, "skips": 1, "input_tokens": 160}
    assert days["2026-09-17"] == {"checks": 1, "blocks": 1, "advisories": 0, "skips": 0, "input_tokens": 5}


def test_run_audit_prints_per_day_report(tmp_path, monkeypatch, repo, capsys):
    monkeypatch.setenv("JEV_REVIEW_STATE_DIR", str(tmp_path / "state"))
    cfg = load_config(repo)
    store = Store(cfg, repo)
    write_audit_day(store, "2026-09-16", [
        {"outcome": "block", "usage": {"input_tokens": 42}},
        {"outcome": "advise", "usage": {"input_tokens": 8}},
    ])
    monkeypatch.chdir(repo)

    rc = run_audit()
    out = capsys.readouterr().out

    assert rc == 0
    assert "2026-09-16" in out
    line = next(l for l in out.splitlines() if l.startswith("2026-09-16"))
    fields = line.split()
    assert fields[1:] == ["2", "1", "1", "0", "50"]


def test_run_audit_no_records(tmp_path, monkeypatch, repo, capsys):
    monkeypatch.setenv("JEV_REVIEW_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.chdir(repo)

    rc = run_audit()
    out = capsys.readouterr().out

    assert rc == 0
    assert "no audit records" in out


def test_run_audit_outside_git_repo(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JEV_REVIEW_STATE_DIR", str(tmp_path / "state"))
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(plain)

    rc = run_audit()
    out = capsys.readouterr().out

    assert rc == 1
    assert "not a git repository" in out
