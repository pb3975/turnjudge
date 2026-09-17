"""SPEC 10 experiment: whole-turn state (all files of a commit in one request) vs per-file answers on the labeled set."""
import json, sys, time
from pathlib import Path
from jev_review.calibrate import load_labels
from jev_review.config import load_config, load_standards
from jev_review.delta import commit_files, commit_message, file_deltas, repo_language, git, EMPTY_TREE
from jev_review.redact import redact_diff, redact_text
from jev_review.questions import questions, NOUL_IDS
from jev_review.client import JevClient
from jev_review.policy import Answers

cfg = load_config(None)
entries = load_labels(Path("calibration/labels.yaml"))
by_sha = {}
for e in entries:
    by_sha.setdefault((str(e.repo), e.sha), []).append(e)
qs = questions()
out = []
with JevClient(model=cfg.model, timeout=45) as client:
    for (repo, sha), es in by_sha.items():
        repo = Path(repo)
        subject, body = commit_message(repo, sha)
        parents = git(repo, "rev-list", "--parents", "-n", "1", sha).split()
        parent = parents[1] if len(parents) > 1 else EMPTY_TREE
        deltas = [d for d in file_deltas(repo, parent, sha) if d.judged]
        files, total = [], 0
        for d in deltas:
            r = redact_diff(d.path, d.diff, per_file_bytes=cfg.per_file_bytes)
            if r.withheld_reason: continue
            if total + len(r.text) > cfg.max_total_bytes: break
            total += len(r.text)
            files.append({"path": d.path, "language": d.language, "status": d.status, "lines_added": d.lines_added,
                          "lines_removed": d.lines_removed, "diff": r.text})
        state = {"task": redact_text(subject + ("\n\n" + body if body else ""), cfg.prompt_bytes, "task"),
                 "standards": load_standards(cfg, repo), "repo": {"name": repo.name, "language": repo_language(repo)},
                 "files": files, "turn_summary": body or "(historical commit: no agent summary)",
                 "note": "This state holds every file the turn changed; judge the turn as a whole."}
        j = client.judge(state, qs)
        a = Answers(j.raw).flat() if j.ok else {"error": j.error}
        rec = {"repo": repo.name, "sha": sha, "n_files_sent": len(files), "n_files_total": len(deltas), "bytes": total,
               "seconds": round(j.seconds, 2), "tokens": (j.raw or {}).get("usage", {}).get("input_tokens"),
               "labels_any_yes": {q: any(str(e.labels.get(q)).lower() in ("yes", "true") for e in es) for q in NOUL_IDS},
               "per_file_max": {}, "turn": a}
        for q in NOUL_IDS:
            vals = []
            for e in es:
                p = Path("calibration/responses") / f"{e.key}.json"
                if p.is_file():
                    v = Answers(json.loads(p.read_text())["response"]).noul(q)
                    if v is not None: vals.append(v)
            rec["per_file_max"][q] = round(max(vals), 2) if vals else None
        out.append(rec)
        print(f"{repo.name} {sha[:7]} files {len(files)}/{len(deltas)} {total}B {j.seconds:.1f}s tokens={rec['tokens']}", flush=True)
Path(sys.argv[1]).write_text(json.dumps(out, indent=1))
print("\n| repo | sha | files | swall label | swall per-file max | swall turn | unreq label | unreq per-file max | unreq turn | tests label(any no) | tests turn |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for r in out:
    t = r["turn"]
    print(f"| {r['repo']} | {r['sha'][:7]} | {r['n_files_sent']}/{r['n_files_total']} | {r['labels_any_yes']['swallows_failure']} | {r['per_file_max']['swallows_failure']} | {t.get('swallows_failure')} | "
          f"{r['labels_any_yes']['unrequested_behavior_change']} | {r['per_file_max']['unrequested_behavior_change']} | {t.get('unrequested_behavior_change')} | "
          f"{not r['labels_any_yes']['tests_proportional']} | {t.get('tests_proportional')} |")
