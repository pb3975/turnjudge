# Calibration experiments

## Whole-turn state vs per-file state (SPEC section 10, first question)

Run 2026-09-16 with `scripts/turn_experiment.py` over the 25 commits behind the 38 labeled deltas.
Each commit's judgeable files were sent in one request as a `files` array (capped at 60 KB, so
large commits were truncated) and the same questions asked once for the whole turn. Results in
`whole-turn-2026-09-16.json`. Compared with the maximum per-file answer for the same commit:

| question | per-file max on positives | whole-turn on positives | per-file max on clean (highest) | whole-turn on clean (highest) |
|---|---|---|---|---|
| swallows_failure (2 positives) | 0.72, 0.46 | 0.36, 0.31 | 0.59 | 0.30 |
| unrequested_behavior_change (2 positives) | 0.83, 0.80 | 0.68, 0.62 | 0.47 | 0.44 |

Whole-turn answers are lower on positives and lower on clean deltas alike: the signal is diluted
by the other files in the turn, and truncation at 60 KB drops files entirely (agentic-sw-factory
commits sent 10 to 28 of 36 to 60 files). Cost per commit was 7k to 24k input tokens against about
6k per file, so a whole-turn request is cheaper only for turns with more than about four files.
Latency stayed under 0.6 s per request.

Conclusion for v1: keep per-file as the unit of review. The `turn_files_changed` list already
gives each per-file request the names and line counts of its siblings. A whole-turn request is
worth revisiting for `unrequested_behavior_change` only if per-file misses accumulate in dogfood.
