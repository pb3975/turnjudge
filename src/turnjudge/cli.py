"""turnjudge CLI: mark | check | calibrate | explain | doctor | init | audit.

Hook-facing commands (mark, check) must never exit non-zero or print anything but hook JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from turnjudge import __version__
from turnjudge.config import PACKAGE_ROOT, load_config


def _calibrate(a: argparse.Namespace) -> int:
    from turnjudge import calibrate as cal
    cfg = load_config(None, Path(a.config) if a.config else None)
    if a.sub == "candidates":
        rows = cal.candidates(Path(a.repo).expanduser(), a.range, a.max_commits, a.min_lines)
        for r in rows:
            print(f"{r['sha'][:10]} {r['date']} {r['lang']:<10} +{r['added']:<4} -{r['removed']:<4} {r['file']}  # {r['subject'][:70]}")
        print(f"{len(rows)} candidates", file=sys.stderr)
        return 0
    if a.sub == "baseline":
        out = Path(a.out) if a.out else PACKAGE_ROOT / "calibration" / "baseline" / f"{Path(a.repo).expanduser().name}.json"
        s = cal.baseline(Path(a.repo).expanduser(), a.range, cfg, out, max_commits=a.max_commits, max_files=a.max_files,
                         workers=a.workers)
        print(f"baseline written to {out}: n={s['n']} errors={s['errors']}")
        return 0
    # run
    labels = Path(a.labels)
    entries = cal.load_labels(labels)
    responses = Path(a.responses)
    standards_override = Path(a.standards).read_text() if a.standards else None
    records = cal.run_entries(entries, cfg, responses, refresh=a.refresh, dry_run=a.dry_run, workers=a.workers,
                              standards_override=standards_override)
    if a.dry_run:
        return 0
    latency_file = Path(a.responses) / "latency.json"
    latency = None
    if a.latency:
        latency = _latency_probe(cfg, entries, records)
        latency_file.write_text(json.dumps(latency))
    elif latency_file.is_file():
        latency = json.loads(latency_file.read_text())
    text = cal.report(entries, records, cfg.thresholds, latency)
    out = Path(a.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(text)
    print(f"\nreport written to {out}", file=sys.stderr)
    return 0


def _latency_probe(cfg, entries, records) -> dict:
    """Six requests in flight against six recorded states; wall time is what the Stop hook would see."""
    import time
    from concurrent.futures import ThreadPoolExecutor
    from turnjudge.client import JevClient
    from turnjudge.questions import questions
    states = [records[e.key]["state"] for e in entries if e.key in records and records[e.key].get("state")][:6]
    if len(states) < 6:
        return {"error": f"only {len(states)} states available"}
    qs = questions()
    t0 = time.monotonic()
    with JevClient(model=cfg.model, timeout=cfg.timeout_seconds) as c, ThreadPoolExecutor(6) as pool:
        js = list(pool.map(lambda s: c.judge(s, qs), states))
    wall = time.monotonic() - t0
    return {"files": 6, "wall_seconds": round(wall, 2), "per_request_seconds": [round(j.seconds, 2) for j in js],
            "errors": sum(1 for j in js if not j.ok), "measured_at": __import__("datetime").datetime.now().isoformat(timespec="seconds")}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="turnjudge", description="End-of-turn semantic review for coding agents.")
    ap.add_argument("--version", action="version", version=f"turnjudge {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("mark", "check"):
        p = sub.add_parser(name, help=f"{name} hook entry point (reads hook JSON on stdin)")
        p.add_argument("--explain", action="store_true", help="print the per-file answer table instead of hook JSON")
        p.add_argument("--event", default=None, help="override hook_event_name (Stop|SubagentStop)")
        p.add_argument("--config", default=None)

    p = sub.add_parser("explain", help="review the current delta on demand and print the answer table")
    p.add_argument("--config", default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--range", default=None, help="review a commit range instead of the working tree, e.g. main..feature")

    p = sub.add_parser("doctor", help="verify key, git, config")
    p.add_argument("--quiet", action="store_true", help="hook mode: print systemMessage JSON only if something is off")
    p.add_argument("--config", default=None)

    p = sub.add_parser("init", help="write .turnjudge.toml and STANDARDS.md into a project")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("audit", help="per-day summary of this project's audit log")
    p.add_argument("--config", default=None)

    p = sub.add_parser("feedback", help="mark an audited block as helpful or not")
    p.add_argument("session_prefix")
    p.add_argument("mark", choices=["helpful", "unhelpful", "list"])
    p.add_argument("--note", default="")
    p.add_argument("--config", default=None)

    c = sub.add_parser("calibrate", help="calibration lab")
    cs = c.add_subparsers(dest="sub", required=True)
    r = cs.add_parser("run", help="judge labeled deltas and write the report")
    r.add_argument("--labels", default="calibration/labels.yaml")
    r.add_argument("--responses", default="calibration/responses")
    r.add_argument("--report", default="calibration/report.md")
    r.add_argument("--standards", default=None, help="use this standards file for every repo")
    r.add_argument("--refresh", action="store_true", help="re-ask even when a response is recorded")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--latency", action="store_true", help="also run the 6-file wall-time probe")
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--config", default=None)
    k = cs.add_parser("candidates", help="list judgeable file deltas in a commit range")
    k.add_argument("--repo", required=True)
    k.add_argument("--range", default="HEAD")
    k.add_argument("--max-commits", type=int, default=200)
    k.add_argument("--min-lines", type=int, default=3)
    k.add_argument("--config", default=None)
    b = cs.add_parser("baseline", help="unlabeled distribution over a repo's history")
    b.add_argument("--repo", required=True)
    b.add_argument("--range", default="HEAD")
    b.add_argument("--max-commits", type=int, default=60)
    b.add_argument("--max-files", type=int, default=150)
    b.add_argument("--workers", type=int, default=6)
    b.add_argument("--out", default=None)
    b.add_argument("--config", default=None)
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.cmd == "calibrate":
        return _calibrate(a)
    from turnjudge import hooks
    if a.cmd in ("mark", "check"):
        return hooks.run_hook(a.cmd, explain=a.explain, event_override=a.event, config_path=a.config)
    if a.cmd == "explain":
        return hooks.run_explain(config_path=a.config, as_json=a.json, rev_range=a.range)
    if a.cmd == "doctor":
        return hooks.run_doctor(quiet=a.quiet, config_path=a.config)
    if a.cmd == "init":
        return hooks.run_init(Path(a.path), force=a.force)
    if a.cmd == "feedback":
        return hooks.run_feedback(a.session_prefix, a.mark, a.note, config_path=a.config)
    if a.cmd == "audit":
        from turnjudge import audit
        return audit.run_audit(config_path=a.config)
    ap.error(f"unknown command {a.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
