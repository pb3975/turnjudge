"""Print the READINESS dogfood table from every project's audit log under the state dir."""
import json, sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "~/.local/state/jev-review").expanduser()
marks = {}
for fb in root.glob("*/feedback.jsonl"):
    for line in fb.read_text().splitlines():
        if line.strip():
            d = json.loads(line); marks[d["block_id"]] = d["mark"]
rows = {}
for proj in sorted(root.iterdir()):
    for f in sorted((proj / "audit").glob("*.jsonl")) if (proj / "audit").is_dir() else []:
        for line in f.read_text().splitlines():
            if not line.strip(): continue
            r = json.loads(line)
            if r.get("explain") or r.get("session_id") in ("t1", "explain"): continue
            key = (proj.name.rsplit("-", 1)[0], r["session_id"])
            row = rows.setdefault(key, {"date": r["ts"][:10], "checks": 0, "blocks": 0, "advise": 0, "skips": 0, "max_s": 0.0, "rules": set(), "marks": set()})
            row["checks"] += 1
            o = r.get("outcome")
            if o == "block": row["blocks"] += 1
            elif o == "advise": row["advise"] += 1
            elif o == "skipped": row["skips"] += 1
            row["max_s"] = max(row["max_s"], float(r.get("seconds") or 0))
            for x in r.get("files", []): row["rules"].update(x["verdict"]["fired"])
            bid = f"{r['session_id'][:8]}/{r.get('turn', '?')}"
            if o == "block": row["marks"].add(marks.get(bid, "unmarked"))
print("| date | repo | session | checks | blocks | advisories | skipped | max seconds | fired rules | block marks |")
print("|---|---|---|---|---|---|---|---|---|---|")
for (proj, sid), r in sorted(rows.items(), key=lambda kv: kv[1]["date"] + kv[0][1]):
    print(f"| {r['date']} | {proj} | {sid[:8]} | {r['checks']} | {r['blocks']} | {r['advise']} | {r['skips']} | {r['max_s']:.2f} | {', '.join(sorted(r['rules'])) or '-'} | {', '.join(sorted(r['marks'])) or '-'} |")
tot = {k: sum(r[k] for r in rows.values()) for k in ("checks", "blocks", "advise", "skips")}
print(f"\n{len(rows)} sessions, {tot['checks']} checks, {tot['blocks']} blocks, {tot['advise']} advisories, {tot['skips']} skipped, max seconds {max((r['max_s'] for r in rows.values()), default=0):.2f}")
