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

## Question wording v3 (2026-09-17): reverted

An independent reviewer agent re-labeled the set (57 entries, 18 pushback) and suggested five
wording changes: interacting loops for control-flow level 2, a method on an existing interface is
not abstraction level 2, "including new code" up front in `swallows_failure` plus a note that a
requested fallback still counts when it catches more than the named case, unintended regressions
count as unrequested change, and inbound routes count as new external surface. All five were
applied and every entry re-asked (`calibration/responses-v3/`). Against the same labels and the v2
wording (`calibration/responses-v2/`, the shipped set):

| question | v2 best thr / agreement | v3 best thr / agreement | v3 at shipped thr |
|---|---|---|---|
| swallows_failure | 0.50 / 0.96 | 0.30 / 0.95 | same |
| unrequested_behavior_change | 0.55 / 0.93 | 0.50 / 0.93 | FN 3 to 5 |
| new_external_surface | 0.20 / 0.98 | 0.20 / 0.93 | FP 0 to 1 |
| Scores | MAE 0.29 to 0.46 | MAE 0.28 to 0.46 | unchanged |

Worse on two questions, no better on the rest. The v2 wording stays shipped. The reviewer's
criteria notes are kept in `calibration/review-notes.md` for the next iteration; the useful
lesson is that broader criteria pull clean deltas up as much as positives.
