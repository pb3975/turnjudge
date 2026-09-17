"""Calibration lab: historical commits + labels -> agreement report + threshold suggestions.

Also produces per-repo baselines (distributions of every answer over unlabeled history) so a new
delta can be reported as a percentile within its own repo.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from jev_review.client import JevClient
from jev_review.config import Config, load_standards
from jev_review.delta import (GitError, commit_file_delta, commit_files, commit_message, file_deltas, git, list_commits,
                              repo_language, turn_files)
from jev_review.policy import Answers, DEFAULT_THRESHOLDS, decide_file
from jev_review.questions import NOUL_IDS, SCORE_LEVELS, SECURITY_IDS, questions, score_top
from jev_review.redact import trim_identity
from jev_review.state import build_state

NOUL_THRESHOLD_KEY = {
    "unnecessary_complexity": "unnecessary_complexity_block",
    "swallows_failure": "swallows_failure_block",
    "unrequested_behavior_change": "unrequested_change_block",
    "tests_proportional": "tests_missing_advise",   # inverted: low means "missing"
    **{q: "security_block" for q in SECURITY_IDS},
}


@dataclass
class Entry:
    repo: Path
    sha: str
    file: str
    verdict: str            # clean | pushback
    labels: dict[str, Any]
    note: str

    @property
    def key(self) -> str:
        slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", self.file)[-60:]
        return f"{self.sha[:10]}-{slug}"


def _yes(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    s = str(v).strip().lower()
    if s in ("yes", "y", "true", "1"):
        return 1.0
    if s in ("no", "n", "false", "0"):
        return 0.0
    return None


def load_labels(path: Path) -> list[Entry]:
    data = yaml.safe_load(path.read_text()) or []
    if isinstance(data, dict):
        data = data.get("entries", [])
    out = []
    for d in data:
        out.append(Entry(repo=Path(d["repo"]).expanduser(), sha=str(d["sha"]), file=d["file"],
                         verdict=str(d.get("verdict", "")).lower(), labels=d.get("labels", {}) or {},
                         note=str(d.get("note", ""))))
    return out


def entry_state(e: Entry, cfg: Config, standards_override: str | None = None) -> dict[str, Any] | None:
    subject, body = commit_message(e.repo, e.sha)
    d = commit_file_delta(e.repo, e.sha, e.file)
    if d is None or not d.judged:
        return None
    standards = standards_override or load_standards(cfg, e.repo)
    fs = build_state(task=subject + ("\n\n" + body if body else ""), standards=standards,
                     repo_name=e.repo.name, language=repo_language(e.repo), delta=d,
                     turn_summary=body or "(historical commit: no agent summary)", cfg=cfg,
                     turn_files=turn_files(commit_files(e.repo, e.sha)))
    return fs.state


def run_entries(entries: list[Entry], cfg: Config, responses_dir: Path, *, refresh: bool = False,
                dry_run: bool = False, workers: int = 4, standards_override: str | None = None,
                log=print) -> dict[str, dict[str, Any]]:
    """Ask Jev about each labeled delta (or load a recorded response). Returns key -> record."""
    responses_dir.mkdir(parents=True, exist_ok=True)
    records: dict[str, dict[str, Any]] = {}
    todo: list[tuple[Entry, dict[str, Any]]] = []
    for e in entries:
        p = responses_dir / f"{e.key}.json"
        if p.is_file() and not refresh:
            records[e.key] = json.loads(p.read_text())
            continue
        try:
            st = entry_state(e, cfg, standards_override)
        except GitError as ex:
            log(f"  skip {e.key}: {ex}")
            continue
        if st is None:
            log(f"  skip {e.key}: file not judged at that commit (binary, deleted, or missing)")
            continue
        todo.append((e, st))
    log(f"{len(records)} recorded, {len(todo)} to ask")
    if dry_run:
        for e, st in todo:
            (responses_dir / f"{e.key}.state.json").write_text(json.dumps(st, indent=1))
        log(f"dry run: wrote {len(todo)} state payloads to {responses_dir}/. No API calls.")
        return records
    if not todo:
        return records
    qs = questions()
    with JevClient(model=cfg.model, timeout=cfg.timeout_seconds) as client, ThreadPoolExecutor(workers) as pool:
        def one(item: tuple[Entry, dict[str, Any]]) -> tuple[Entry, dict[str, Any], Any]:
            e, st = item
            return e, st, client.judge(st, qs)
        for e, st, j in pool.map(one, todo):
            rec = {"repo": trim_identity(str(e.repo)), "sha": e.sha, "file": e.file, "asked_at": dt.datetime.now().isoformat(timespec="seconds"),
                   "seconds": round(j.seconds, 2), "state": st, "response": j.raw, "error": j.error}
            (responses_dir / f"{e.key}.json").write_text(json.dumps(rec, indent=1))
            records[e.key] = rec
            log(f"  {e.key}: {'ok' if j.ok else j.error} ({j.seconds:.1f}s)")
    return records


# ---- metrics ----------------------------------------------------------------------------

def _agreement(pairs: list[tuple[float, float]], thr: float) -> float:
    if not pairs:
        return float("nan")
    return sum(1 for p, y in pairs if (p >= thr) == (y >= 0.5)) / len(pairs)


def _brier(pairs: list[tuple[float, float]]) -> float:
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs) if pairs else float("nan")


def _best_threshold(pairs: list[tuple[float, float]]) -> tuple[float, float]:
    best_t, best_a = 0.5, -1.0
    for i in range(5, 96, 5):
        t = i / 100
        a = _agreement(pairs, t)
        if a > best_a + 1e-9:
            best_t, best_a = t, a
    return best_t, best_a


def _fmt(x: float | None, nd: int = 2) -> str:
    return "n/a" if x is None or x != x else f"{x:.{nd}f}"


def report(entries: list[Entry], records: dict[str, dict[str, Any]], thresholds: dict[str, float],
           latency: dict[str, Any] | None = None) -> str:
    t = {**DEFAULT_THRESHOLDS, **thresholds}
    used = [(e, records[e.key]) for e in entries if e.key in records and records[e.key].get("response")]
    repos = sorted({e.repo.name for e, _ in used})
    lines = [f"# Calibration report", "",
             f"Generated {dt.datetime.now().isoformat(timespec='minutes')} from {len(used)} labeled file deltas "
             f"across {len(repos)} repos ({', '.join(repos)}). Labels: `calibration/labels.yaml`. "
             f"Responses: `calibration/responses/`.", ""]
    n_clean = sum(1 for e, _ in used if e.verdict == "clean")
    n_push = sum(1 for e, _ in used if e.verdict == "pushback")
    lines += [f"Verdict balance: {n_clean} clean, {n_push} pushback, {len(used) - n_clean - n_push} unmarked.", ""]

    # Nouls
    lines += ["## Noul questions", "",
              "| question | n | shipped thr | agreement @shipped | Brier | best thr | agreement @best | FP @shipped | FN @shipped |",
              "|---|---|---|---|---|---|---|---|---|"]
    for qid in NOUL_IDS:
        pairs = []
        for e, r in used:
            y = _yes(e.labels.get(qid))
            p = Answers(r["response"]).noul(qid)
            if y is None or p is None:
                continue
            pairs.append((p, y))
        thr = t[NOUL_THRESHOLD_KEY[qid]]
        if qid == "tests_proportional":
            # policy fires when p <= thr; agreement is on the "has tests" reading
            agree = sum(1 for p, y in pairs if (p > thr) == (y >= 0.5)) / len(pairs) if pairs else float("nan")
            fp = sum(1 for p, y in pairs if p <= thr and y >= 0.5)
            fn = sum(1 for p, y in pairs if p > thr and y < 0.5)
        else:
            agree = _agreement(pairs, thr)
            fp = sum(1 for p, y in pairs if p >= thr and y < 0.5)
            fn = sum(1 for p, y in pairs if p < thr and y >= 0.5)
        bt, ba = _best_threshold(pairs) if pairs else (float("nan"), float("nan"))
        lines.append(f"| {qid} | {len(pairs)} | {thr:.2f} | {_fmt(agree)} | {_fmt(_brier(pairs), 3)} | {_fmt(bt)} | {_fmt(ba)} | {fp} | {fn} |")
    lines.append("")
    lines.append("FP = fired above threshold on a delta labeled no. FN = stayed below on a delta labeled yes. "
                 "For `tests_proportional` the policy fires when p is at or under the threshold, so FP means "
                 "'flagged as missing tests when labeled proportional'.")
    lines.append("")

    # Scores
    lines += ["## Score questions", "", "| question | n | MAE (levels) | within 0.5 | within 1.0 | mean label | mean answer | mean confidence |",
              "|---|---|---|---|---|---|---|---|"]
    for qid in SCORE_LEVELS:
        pairs, confs = [], []
        for e, r in used:
            y = e.labels.get(qid)
            a = Answers(r["response"])
            s = a.score(qid)
            if y is None or s is None:
                continue
            pairs.append((s, float(y)))
            confs.append(a.confidence(qid) or 0.0)
        if not pairs:
            lines.append(f"| {qid} | 0 | n/a | n/a | n/a | n/a | n/a | n/a |")
            continue
        mae = sum(abs(s - y) for s, y in pairs) / len(pairs)
        w5 = sum(1 for s, y in pairs if abs(s - y) <= 0.5) / len(pairs)
        w1 = sum(1 for s, y in pairs if abs(s - y) <= 1.0) / len(pairs)
        lines.append(f"| {qid} | {len(pairs)} | {mae:.2f} | {w5:.2f} | {w1:.2f} | {statistics.mean(y for _, y in pairs):.2f} | "
                     f"{statistics.mean(s for s, _ in pairs):.2f} | {statistics.mean(confs):.2f} |")
    lines.append("")

    # Policy vs verdict
    lines += ["## Policy outcome vs verdict", "", "Shipped policy applied to each recorded response, compared with the labeler's overall verdict.", "",
              "| verdict | pass | advise | block |", "|---|---|---|---|"]
    conf: dict[str, dict[str, int]] = {"clean": {"pass": 0, "advise": 0, "block": 0}, "pushback": {"pass": 0, "advise": 0, "block": 0}}
    per_entry = []
    for e, r in used:
        v = decide_file(e.file, Answers(r["response"]), t, task=r["state"].get("task", ""))
        if e.verdict in conf:
            conf[e.verdict][v.outcome] += 1
        per_entry.append((e, v))
    for k in ("clean", "pushback"):
        lines.append(f"| {k} | {conf[k]['pass']} | {conf[k]['advise']} | {conf[k]['block']} |")
    lines.append("")
    tot_push = sum(conf["pushback"].values())
    tot_clean = sum(conf["clean"].values())
    if tot_push:
        lines.append(f"Pushback deltas that got at least advise: {(conf['pushback']['advise'] + conf['pushback']['block']) / tot_push:.2f}.")
    if tot_clean:
        lines.append(f"Clean deltas that passed silently: {conf['clean']['pass'] / tot_clean:.2f}. "
                     f"Clean deltas blocked: {conf['clean']['block']}.")
    lines.append("")

    # Per-entry table
    lines += ["## Per-delta answers", "",
              "| repo | sha | file | verdict | outcome | fired | unnec | swall | unreq | tests | secret | input | weaken | extsurf | beh | cflow | abstr | maint | verb |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for e, v in per_entry:
        vals = v.values
        def g(k: str) -> str:
            return _fmt(vals.get(k))
        fired = ",".join(f.rule for f in v.fired) or "-"
        lines.append(f"| {e.repo.name} | {e.sha[:7]} | {e.file[-38:]} | {e.verdict or '-'} | {v.outcome} | {fired} | "
                     f"{g('unnecessary_complexity')} | {g('swallows_failure')} | {g('unrequested_behavior_change')} | {g('tests_proportional')} | "
                     f"{g('introduces_secret')} | {g('unsafe_input_use')} | {g('weakens_check')} | {g('new_external_surface')} | "
                     f"{g('behavior_added')} | {g('control_flow_added')} | {g('abstraction_added')} | {g('maintenance_risk')} | {g('verbosity')} |")
    lines.append("")

    # Usage and latency
    secs = [r.get("seconds", 0) for _, r in used]
    toks_in = [((r.get("response") or {}).get("usage") or {}).get("input_tokens") or 0 for _, r in used]
    toks_out = [((r.get("response") or {}).get("usage") or {}).get("output_tokens") or 0 for _, r in used]
    lines += ["## Cost and latency", "",
              f"- Requests: {len(used)}; input tokens: {sum(toks_in)}; output tokens: {sum(toks_out)}; "
              f"billing_units: not returned by the API (SDK 0.6.0 note).",
              f"- Per-request latency: median {_fmt(statistics.median(secs) if secs else None)} s, "
              f"max {_fmt(max(secs) if secs else None)} s, mean input tokens {_fmt(statistics.mean(toks_in) if toks_in else None, 0)}."]
    if latency:
        lines.append(f"- 6-file wall-time test: {latency}")
    lines.append("")
    # Hand-written assessment survives regeneration: keep it in calibration/assessment.md.
    assessment = Path("calibration/assessment.md")
    if assessment.is_file():
        lines += ["## Assessment", "", assessment.read_text().strip(), ""]
    return "\n".join(lines)


# ---- candidates and baseline -------------------------------------------------------------

def candidates(repo: Path, rev_range: str, max_commits: int = 200, min_lines: int = 3, log=print) -> list[dict]:
    """List judgeable code file deltas over a commit range, for choosing what to label."""
    out = []
    for c in list_commits(repo, rev_range, max_commits):
        try:
            ds = file_deltas(repo, f"{c['sha']}^", c["sha"], context=0, function_context=False)
        except GitError:
            continue
        for d in ds:
            if not d.judged or not d.is_code() or d.lines_added + d.lines_removed < min_lines:
                continue
            out.append({"repo": str(repo), "sha": c["sha"], "date": c["date"], "subject": c["subject"],
                        "file": d.path, "added": d.lines_added, "removed": d.lines_removed, "lang": d.language})
    return out


def baseline(repo: Path, rev_range: str, cfg: Config, out_path: Path, *, max_commits: int = 60,
             max_files: int = 150, workers: int = 6, log=print) -> dict[str, Any]:
    """Unlabeled run over history: per-question distributions for percentile reporting."""
    cands = candidates(repo, rev_range, max_commits, log=log)[:max_files]
    log(f"baseline {repo.name}: {len(cands)} file deltas")
    qs = questions()
    standards = load_standards(cfg, repo)
    lang = repo_language(repo)
    rows: list[dict[str, Any]] = []
    with JevClient(model=cfg.model, timeout=cfg.timeout_seconds) as client, ThreadPoolExecutor(workers) as pool:
        def one(c: dict) -> dict[str, Any] | None:
            subject, body = commit_message(repo, c["sha"])
            d = commit_file_delta(repo, c["sha"], c["file"])
            if d is None or not d.judged:
                return None
            fs = build_state(task=subject + ("\n\n" + body if body else ""), standards=standards, repo_name=repo.name,
                             language=lang, delta=d, turn_summary=body or "(historical commit: no agent summary)", cfg=cfg,
                             turn_files=turn_files(commit_files(repo, c["sha"])))
            if fs.state is None:
                return None
            j = client.judge(fs.state, qs)
            if not j.ok:
                return {"sha": c["sha"], "file": c["file"], "error": j.error}
            return {"sha": c["sha"], "file": c["file"], **Answers(j.raw).flat(), "seconds": round(j.seconds, 2)}
        for r in pool.map(one, cands):
            if r:
                rows.append(r)
    ok = [r for r in rows if "error" not in r]
    dist: dict[str, list[float]] = {}
    for r in ok:
        for k, v in r.items():
            if isinstance(v, float) and k != "seconds":
                dist.setdefault(k, []).append(v)
    summary = {"repo": trim_identity(str(repo)), "range": rev_range, "generated": dt.datetime.now().isoformat(timespec="seconds"),
               "n": len(ok), "errors": len(rows) - len(ok),
               "distributions": {k: sorted(v) for k, v in dist.items()}, "rows": rows}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=1))
    return summary


def percentile(sorted_values: list[float], x: float) -> float:
    if not sorted_values:
        return float("nan")
    below = sum(1 for v in sorted_values if v < x)
    equal = sum(1 for v in sorted_values if v == x)
    return round(100.0 * (below + 0.5 * equal) / len(sorted_values), 1)
