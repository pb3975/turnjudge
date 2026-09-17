"""Hook entry points: mark (UserPromptSubmit), check (Stop/SubagentStop), doctor (SessionStart),
plus the on-demand explain, init, and feedback commands.

Contract (SPEC 3.7 and 3.10): a hook command never exits non-zero, never prints anything but
hook JSON to stdout, and on any failure of its own lets the agent proceed. A block is issued at
most once per turn.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any

from jev_review.config import DEFAULT_STANDARDS_PATH, PACKAGE_ROOT, Config, load_config, load_standards
from jev_review.delta import FileDelta, GitError, file_deltas, git, head_tree, repo_language, repo_root, snapshot_tree, turn_files
from jev_review.policy import (Answers, FileVerdict, T_TOO_LARGE, T_WITHHELD, apply_mode, decide_file, explain_table,
                               render_feedback, worst)
from jev_review.questions import questions
from jev_review.state import build_state
from jev_review.store import Store

NO_KEY_MSG = "jev-review disabled: no key (set TYPESAFE_API_KEY or create ~/.config/jev-review/key)"
UNAVAILABLE_MSG = "jev-review skipped: service unavailable"


def _read_stdin_json() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    raw = raw.strip()
    if not raw:
        return {}
    try:
        d = json.loads(raw)
        return d if isinstance(d, dict) else {}
    except json.JSONDecodeError:
        return {}


def _emit(obj: dict[str, Any] | None) -> None:
    if obj:
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()


def _git_emails(repo: Path) -> list[str]:
    out = []
    for key in ("user.email",):
        try:
            v = git(repo, "config", "--get", key, check=False).strip()
            if v:
                out.append(v)
        except GitError:
            pass
    return out


# ---- mark ------------------------------------------------------------------------------------

def do_mark(payload: dict[str, Any], cfg: Config) -> None:
    cwd = Path(payload.get("cwd") or os.getcwd())
    repo = repo_root(cwd)
    if repo is None:
        return
    store = Store(cfg, repo)
    session_id = str(payload.get("session_id") or "unknown")
    s = store.load_session(session_id)
    tree = snapshot_tree(repo)
    prompt = str(payload.get("prompt") or "")
    s.update({
        "tree": tree,
        "prompt": prompt[: cfg.prompt_bytes * 2],
        "marked_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "turn": int(s.get("turn", 0)) + 1,
        "blocked_turn": s.get("blocked_turn"),
    })
    store.save_session(session_id, s)


# ---- check -----------------------------------------------------------------------------------

def _baseline_for(cfg: Config, repo: Path) -> dict[str, list[float]] | None:
    for p in (cfg.state_root() / "baselines" / f"{repo.name}.json",
              repo / ".jev-review" / "baseline.json"):
        if p.is_file():
            try:
                return json.loads(p.read_text()).get("distributions")
            except (OSError, json.JSONDecodeError):
                return None
    return None


def _percentile_note(baseline: dict[str, list[float]] | None, v: FileVerdict) -> str:
    if not baseline or not v.fired:
        return ""
    from jev_review.calibrate import percentile
    rule = v.fired[0].rule
    key = rule if rule in v.values else None
    if key is None or key not in baseline:
        return ""
    return f" ({key} at the {percentile(baseline[key], v.values[key]):.0f}th percentile for this repo)"


class CheckResult:
    def __init__(self) -> None:
        self.outcome = "pass"
        self.output: dict[str, Any] | None = None
        self.verdicts: list[FileVerdict] = []
        self.notes: list[str] = []
        self.audit_path: Path | None = None
        self.skipped_reason: str | None = None


def do_check(payload: dict[str, Any], cfg: Config, *, event: str, explain: bool = False,
             session_override: str | None = None) -> CheckResult:
    res = CheckResult()
    t_start = time.monotonic()
    cwd = Path(payload.get("cwd") or os.getcwd())
    repo = repo_root(cwd)
    if repo is None:
        res.skipped_reason = "no git repo"
        return res
    store = Store(cfg, repo)
    session_id = session_override or str(payload.get("session_id") or "unknown")
    s = store.load_session(session_id)

    # Loop guard: never block twice in one turn.
    if payload.get("stop_hook_active") is True and not explain:
        res.skipped_reason = "stop_hook_active"
        return res
    turn = int(s.get("turn", 0))
    if not explain and s.get("blocked_turn") is not None and s.get("blocked_turn") == turn:
        res.skipped_reason = "already blocked this turn"
        return res

    mode = cfg.mode
    if event == "SubagentStop":
        mode = cfg.subagents
    if mode == "off" and not explain:
        res.skipped_reason = "mode off"
        return res

    # Delta
    fallback = False
    start = s.get("tree")
    if not start:
        start, fallback = head_tree(repo), True
    end = snapshot_tree(repo)
    if start == end:
        res.skipped_reason = "no changes"
        return res
    deltas = file_deltas(repo, start, end)
    judged = [d for d in deltas if d.judged]
    skipped = [d for d in deltas if not d.judged]
    if not judged:
        res.skipped_reason = "no judgeable files"
        s["tree"] = end
        store.save_session(session_id, s)
        return res

    task = s.get("prompt") or str(payload.get("prompt") or "")
    summary = str(payload.get("last_assistant_message") or "")
    standards = load_standards(cfg, repo)
    language = repo_language(repo)
    emails = _git_emails(repo)
    tf = turn_files(deltas)
    states = [build_state(task=task, standards=standards, repo_name=repo.name, language=language, delta=d,
                          turn_summary=summary, cfg=cfg, emails=emails, turn_files=tf) for d in judged]
    withheld = [fs for fs in states if fs.state is None]
    sendable = [fs for fs in states if fs.state is not None]
    total_bytes = sum(len(fs.redacted.text.encode("utf-8")) for fs in sendable)
    advisory_only = False
    if len(sendable) > cfg.max_files or total_bytes > cfg.max_total_bytes:
        advisory_only = True
        res.notes.append(T_TOO_LARGE.format(files=len(sendable), bytes=total_bytes))
        sendable = sendable[: cfg.max_files]
    if withheld:
        res.notes.append(T_WITHHELD.format(n=len(withheld), paths=", ".join(fs.path for fs in withheld)[:500]))
    if not sendable:
        res.outcome = "pass"
        res.output = {"systemMessage": "\n".join(res.notes)} if res.notes else None
        s["tree"] = end
        store.save_session(session_id, s)
        store.audit({"session_id": session_id, "event": event, "start_tree": start, "end_tree": end,
                     "fallback_to_head": fallback, "files": [], "withheld": [fs.path for fs in withheld],
                     "outcome": "pass", "notes": res.notes, "explain": explain})
        return res

    # Client
    from jev_review.client import KeyError_, make_client
    try:
        client = make_client(model=cfg.model, timeout=cfg.timeout_seconds)
    except KeyError_ as e:
        store.log_error("check", note=str(e))
        if not s.get("notified_no_key"):
            res.output = {"systemMessage": NO_KEY_MSG}
            s["notified_no_key"] = True
        s["tree"] = end
        store.save_session(session_id, s)
        res.skipped_reason = "no key"
        return res

    qs = questions()
    budget = max(1.0, cfg.timeout_seconds - (time.monotonic() - t_start) - 2.0)
    judgments: dict[str, Any] = {}
    with client:
        pool = ThreadPoolExecutor(max_workers=max(1, min(cfg.workers, len(sendable))))
        futs = {pool.submit(client.judge, fs.state, qs): fs for fs in sendable}
        done, pending = wait(futs, timeout=budget)
        for f in done:
            judgments[futs[f].path] = f.result()
        for f in pending:
            f.cancel()
        pool.shutdown(wait=False, cancel_futures=True)
    ok = {p: j for p, j in judgments.items() if j.ok}
    failed = {p: j for p, j in judgments.items() if not j.ok}
    timed_out = [fs.path for fs in sendable if fs.path not in judgments]
    if not ok:
        kinds = {j.error_kind for j in failed.values()}
        store.log_error("check", note=f"all {len(sendable)} requests failed: kinds={kinds} timed_out={timed_out}")
        if kinds == {"auth"}:
            if not s.get("notified_no_key"):
                res.output = {"systemMessage": NO_KEY_MSG}
                s["notified_no_key"] = True
        else:
            res.output = {"systemMessage": UNAVAILABLE_MSG}
        res.skipped_reason = "service unavailable"
        s["tree"] = end
        store.save_session(session_id, s)
        store.audit({"session_id": session_id, "event": event, "start_tree": start, "end_tree": end,
                     "fallback_to_head": fallback, "outcome": "skipped", "reason": res.skipped_reason,
                     "errors": {p: j.error for p, j in failed.items()}, "timed_out": timed_out, "explain": explain})
        return res

    # Policy
    baseline = _baseline_for(cfg, repo)
    verdicts: list[FileVerdict] = []
    for fs in sendable:
        j = ok.get(fs.path)
        if j is None:
            continue
        v = decide_file(fs.path, Answers(j.raw), cfg.thresholds, task=task)
        verdicts.append(v)
    res.verdicts = verdicts
    outcome = worst(verdicts)
    if advisory_only and outcome == "block":
        outcome = "advise"
    outcome = apply_mode(outcome, mode)
    if explain:
        outcome_effective = outcome
    else:
        outcome_effective = outcome
    res.outcome = outcome_effective

    feedback = render_feedback(verdicts, blocking=(outcome_effective == "block"))
    if baseline:
        for v in verdicts:
            note = _percentile_note(baseline, v)
            if note and v.fired:
                feedback = feedback.replace(v.fired[0].message, v.fired[0].message + note, 1)
    if failed or timed_out:
        res.notes.append(f"jev-review: {len(failed) + len(timed_out)} file(s) could not be judged this turn.")
    text = "\n".join([feedback, *res.notes]).strip()

    if not explain:
        if outcome_effective == "block":
            res.output = {"decision": "block", "reason": text}
            s["blocked_turn"] = turn
            s["blocks"] = int(s.get("blocks", 0)) + 1
        elif outcome_effective == "advise" and text:
            res.output = {"systemMessage": text}
        elif text:
            res.output = {"systemMessage": text}
    if not explain:  # an on-demand explain must not move the turn's start tree
        s["tree"] = end
        s["last_check"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        store.save_session(session_id, s)

    usage_in = sum(((j.raw or {}).get("usage") or {}).get("input_tokens") or 0 for j in ok.values())
    usage_out = sum(((j.raw or {}).get("usage") or {}).get("output_tokens") or 0 for j in ok.values())
    res.audit_path = store.audit({
        "session_id": session_id, "event": event, "turn": turn, "start_tree": start, "end_tree": end,
        "fallback_to_head": fallback, "advisory_only": advisory_only, "mode": mode, "explain": explain,
        "outcome": outcome_effective, "feedback": text,
        "usage": {"input_tokens": usage_in, "output_tokens": usage_out, "billing_units": None},
        "seconds": round(time.monotonic() - t_start, 2),
        "withheld": [fs.path for fs in withheld], "skipped": [{"path": d.path, "reason": d.skip_reason} for d in skipped],
        "errors": {p: j.error for p, j in failed.items()}, "timed_out": timed_out,
        "files": [{"path": fs.path, "state": fs.state, "response": ok[fs.path].raw,
                   "verdict": {"outcome": v.outcome, "fired": [f.rule for f in v.fired], "composite": v.composite}}
                  for fs, v in zip([fs for fs in sendable if fs.path in ok], verdicts)],
    })
    return res


# ---- entry points ----------------------------------------------------------------------------

def run_hook(cmd: str, *, explain: bool = False, event_override: str | None = None, config_path: str | None = None) -> int:
    """mark | check from a hook. Always exits 0; stdout is hook JSON or nothing."""
    payload = _read_stdin_json()
    cfg = None
    try:
        cwd = Path(payload.get("cwd") or os.getcwd())
        cfg = load_config(repo_root(cwd), Path(config_path) if config_path else None)
        if cmd == "mark":
            do_mark(payload, cfg)
            return 0
        event = event_override or str(payload.get("hook_event_name") or "Stop")
        res = do_check(payload, cfg, event=event, explain=explain)
        if explain:
            _print_explain(res)
        else:
            _emit(res.output)
        _hard_exit(0)
    except Exception as e:  # never reach the agent
        try:
            repo = repo_root(Path(payload.get("cwd") or os.getcwd()))
            if cfg is not None and repo is not None:
                Store(cfg, repo).log_error(cmd, e)
            else:
                _fallback_error_log(cmd, e)
        except Exception:
            pass
        _hard_exit(0)
    return 0


def _hard_exit(code: int) -> None:
    """Exit without waiting for worker threads: a request still sleeping in the SDK must not hold
    the hook open past its budget. Output is flushed first."""
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(code)


def _fallback_error_log(where: str, exc: BaseException) -> None:
    import traceback
    p = Path("~/.local/state/jev-review/errors.log").expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')} {where}\n")
        f.write("".join(traceback.format_exception(exc)))


def _print_explain(res: CheckResult) -> None:
    if res.skipped_reason and not res.verdicts:
        print(f"jev-review: nothing to review ({res.skipped_reason})")
        return
    print(explain_table(res.verdicts))
    print()
    print(f"turn outcome: {res.outcome}")
    for v in res.verdicts:
        for f in v.fired:
            print(f"- [{f.outcome}] {f.message}")
    for n in res.notes:
        print(f"- {n}")
    if res.audit_path:
        print(f"audit: {res.audit_path}")


def run_explain(*, config_path: str | None = None, as_json: bool = False) -> int:
    """On demand: review the working tree against HEAD (or against the session mark if JEV_REVIEW_SESSION is set)."""
    cwd = Path(os.getcwd())
    repo = repo_root(cwd)
    if repo is None:
        print("jev-review: not a git repository")
        return 1
    cfg = load_config(repo, Path(config_path) if config_path else None)
    session = os.environ.get("JEV_REVIEW_SESSION") or "explain"
    payload = {"cwd": str(cwd), "session_id": session, "prompt": os.environ.get("JEV_REVIEW_TASK", "")}
    try:
        res = do_check(payload, cfg, event="Stop", explain=True, session_override=session)
    except Exception as e:
        print(f"jev-review: error: {type(e).__name__}: {e}")
        return 1
    if as_json:
        print(json.dumps({"outcome": res.outcome, "skipped": res.skipped_reason, "notes": res.notes,
                          "files": [{"path": v.path, "outcome": v.outcome, "fired": [f.rule for f in v.fired],
                                     "values": v.values} for v in res.verdicts]}, indent=1))
    else:
        _print_explain(res)
    # The explain session must not carry a stale tree into the next call: reset so the next explain
    # judges the full uncommitted delta again.
    Store(cfg, repo).save_session(session, {})
    return 0


# ---- doctor ----------------------------------------------------------------------------------

def doctor_checks(cfg: Config, repo: Path | None) -> list[tuple[str, bool, str]]:
    from jev_review.client import KEY_FILE, key_file_mode_ok, key_source
    checks: list[tuple[str, bool, str]] = []
    src = key_source()
    if src == "none":
        checks.append(("key", False, NO_KEY_MSG))
    elif src.startswith("file:"):
        if key_file_mode_ok():
            checks.append(("key", True, f"key file {KEY_FILE} (mode 0600)"))
        else:
            checks.append(("key", False, f"{KEY_FILE} is group- or world-readable; run: chmod 600 {KEY_FILE}"))
    else:
        checks.append(("key", True, "key from TYPESAFE_API_KEY"))
    checks.append(("git", shutil.which("git") is not None, "git on PATH" if shutil.which("git") else "git not found on PATH"))
    if repo is None:
        checks.append(("repo", False, "not inside a git repository (mark/check will do nothing here)"))
    else:
        checks.append(("repo", True, f"repo {repo.name}"))
        p = repo / cfg.standards
        checks.append(("standards", True, f"standards: {p}" if p.is_file() else f"standards: default ({DEFAULT_STANDARDS_PATH.name}); run `jev-review init` to add {cfg.standards}"))
    try:
        cfg.state_root().mkdir(parents=True, exist_ok=True)
        checks.append(("state", True, f"state dir {cfg.state_root()}"))
    except OSError as e:
        checks.append(("state", False, f"state dir not writable: {e}"))
    checks.append(("config", True, "config: " + ", ".join(cfg.source_files)))
    checks.append(("mode", True, f"mode={cfg.mode} subagents={cfg.subagents} timeout={cfg.timeout_seconds}s model={cfg.model}"))
    return checks


def run_doctor(*, quiet: bool = False, config_path: str | None = None) -> int:
    payload = _read_stdin_json() if quiet else {}
    try:
        cwd = Path(payload.get("cwd") or os.getcwd())
        repo = repo_root(cwd)
        cfg = load_config(repo, Path(config_path) if config_path else None)
        checks = doctor_checks(cfg, repo)
    except Exception as e:
        if quiet:
            return 0
        print(f"jev-review doctor: error: {type(e).__name__}: {e}")
        return 1
    bad = [c for c in checks if not c[1]]
    if quiet:
        if bad and repo is not None:
            _emit({"systemMessage": "jev-review: " + "; ".join(c[2] for c in bad)})
        return 0
    for name, ok, msg in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {name:<10} {msg}")
    if bad:
        print(f"\n{len(bad)} problem(s).")
        return 1
    # live probe when everything else passes and a key is present
    try:
        from jev_review.client import make_client
        from typesafe_sdk import Noul
        with make_client(model=cfg.model, timeout=min(cfg.timeout_seconds, 15.0)) as c:
            j = c.judge({"probe": "jev-review doctor"}, {"ok": Noul(instructions="Is `probe` a short string?")})
        if j.ok:
            print(f"ok   api        reachable ({j.seconds:.2f}s, model {j.raw.get('model')})")
        else:
            print(f"FAIL api        {j.error}")
            return 1
    except Exception as e:
        print(f"FAIL api        {type(e).__name__}: {e}")
        return 1
    print("\nall checks passed.")
    return 0


# ---- init ------------------------------------------------------------------------------------

INIT_TOML = """# jev-review project overrides. Defaults live in the plugin's jev-review.toml.

[review]
# mode = "block"          # block | advise | off
# subagents = "advise"

[thresholds]
# Every value is uncalibrated until calibration/report.md in the jev-review repo says otherwise.
# security_block = 0.85
# swallows_failure_block = 0.85
# unrequested_change_block = 0.80

[redact]
deny_paths = []          # globs never sent, e.g. ["infra/secrets/**"]
extra_patterns = []      # extra secret regexes

[paths]
standards = "STANDARDS.md"
"""


def run_init(path: Path, *, force: bool = False) -> int:
    root = repo_root(path) or path
    wrote = []
    toml = root / ".jev-review.toml"
    std = root / "STANDARDS.md"
    if force or not toml.exists():
        toml.write_text(INIT_TOML)
        wrote.append(str(toml))
    if force or not std.exists():
        std.write_text(DEFAULT_STANDARDS_PATH.read_text())
        wrote.append(str(std))
    for w in wrote:
        print(f"wrote {w}")
    if not wrote:
        print("nothing to do (files exist; use --force to overwrite)")
    return 0


# ---- feedback --------------------------------------------------------------------------------

def _iter_audit_blocks(store: Store):
    for p in store.audit_files():
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("outcome") == "block" and not r.get("explain"):
                yield p, r


def run_feedback(session_prefix: str, mark: str, note: str, *, config_path: str | None = None) -> int:
    cwd = Path(os.getcwd())
    repo = repo_root(cwd)
    if repo is None:
        print("jev-review: not a git repository")
        return 1
    cfg = load_config(repo, Path(config_path) if config_path else None)
    store = Store(cfg, repo)
    fb_path = store.root / "feedback.jsonl"
    marks: dict[str, dict] = {}
    if fb_path.is_file():
        for line in fb_path.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                marks[d["block_id"]] = d
    blocks = list(_iter_audit_blocks(store))
    if mark == "list":
        for p, r in blocks:
            bid = f"{r['session_id'][:8]}/{r.get('turn', '?')}"
            m = marks.get(bid, {}).get("mark", "-")
            print(f"{bid:<14} {r['ts']} {m:<10} {r['feedback'][:90].replace(chr(10), ' ')}")
        print(f"{len(blocks)} block(s), {sum(1 for b in marks.values() if b['mark']=='helpful')} helpful, "
              f"{sum(1 for b in marks.values() if b['mark']=='unhelpful')} unhelpful")
        return 0
    matched = [(p, r) for p, r in blocks if r["session_id"].startswith(session_prefix.split("/")[0])
               and ("/" not in session_prefix or str(r.get("turn")) == session_prefix.split("/")[1])]
    if not matched:
        print(f"no block found for {session_prefix}; run `jev-review feedback x list`")
        return 1
    with fb_path.open("a") as f:
        for p, r in matched:
            bid = f"{r['session_id'][:8]}/{r.get('turn', '?')}"
            f.write(json.dumps({"block_id": bid, "session_id": r["session_id"], "turn": r.get("turn"), "mark": mark,
                                "note": note, "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}) + "\n")
            print(f"marked {bid} {mark}")
    return 0
