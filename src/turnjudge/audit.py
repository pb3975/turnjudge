"""audit: per-day summary of this project's audit log (checks, blocks, advisories, skips, tokens)."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path

from turnjudge.config import load_config
from turnjudge.delta import repo_root
from turnjudge.store import Store

DayStats = dict[str, int]


def _empty_day() -> DayStats:
    return {"checks": 0, "blocks": 0, "advisories": 0, "skips": 0, "input_tokens": 0}


def daily_summary(store: Store) -> dict[str, DayStats]:
    days: dict[str, DayStats] = defaultdict(_empty_day)
    for p in store.audit_files():
        day = p.stem
        d = days[day]
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            d["checks"] += 1
            outcome = r.get("outcome")
            if outcome == "block":
                d["blocks"] += 1
            elif outcome == "advise":
                d["advisories"] += 1
            elif outcome == "skipped":
                d["skips"] += 1
            d["input_tokens"] += int(((r.get("usage") or {}).get("input_tokens")) or 0)
    return dict(days)


def run_audit(*, config_path: str | None = None) -> int:
    cwd = Path(os.getcwd())
    repo = repo_root(cwd)
    if repo is None:
        print("turnjudge: not a git repository")
        return 1
    cfg = load_config(repo, Path(config_path) if config_path else None)
    store = Store(cfg, repo)
    days = daily_summary(store)
    if not days:
        print("turnjudge: no audit records")
        return 0
    print(f"{'date':<12} {'checks':>6} {'blocks':>6} {'advise':>6} {'skips':>6} {'in_tokens':>10}")
    for day in sorted(days):
        d = days[day]
        print(f"{day:<12} {d['checks']:>6} {d['blocks']:>6} {d['advisories']:>6} {d['skips']:>6} {d['input_tokens']:>10}")
    return 0
