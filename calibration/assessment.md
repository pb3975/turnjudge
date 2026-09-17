Written by the builder agent after the Phase 0 runs on 2026-09-16. Numbers above are regenerated
from `calibration/responses/`; this section is hand-written and kept in `calibration/assessment.md`.

**What the set is.** 38 file deltas from real commits: 17 nests (Go), 12 agentic-sw-factory
(TypeScript), 3 qb-harness (Python), 3 billy-blog (Svelte/TS, shell), plus 3 more nests deltas
traced from later review-fix commits. 28 are labeled clean and 10 pushback. The pushback cases
were found by reading "fix: address review" commits and labeling the delta they corrected, so
each one is a defect a human reviewer actually caught. The labels are the builder's, not Will's;
the criteria text in `questions.py` was applied as literally as possible and each `note` says why.

**Latency and cost.** Median 0.25 s per request, 6 requests in flight complete in about 0.5 s
wall time (see the probe above), about 6,100 input tokens per file delta with function context.
The 8 s budget in SPEC section 6 is met with a wide margin; a 12-file turn would cost roughly
75k input tokens.

**Scores (criterion 3 asks MAE at or under 0.6).** All five Scores are within 0.27 to 0.45 levels
of the labels and 89 to 100 percent of answers land within one level. The model reads every scale
about 0.3 levels higher than the labeler, consistently. Confidence is lowest on `verbosity`
(0.54) and `maintenance_risk` (0.64), which are the two most judgment-laden scales.

**Nouls: what the agreement numbers do and do not say.** Agreement at the shipped thresholds is
0.84 to 1.00, but most of that is the model and the labeler both saying no. The set has zero
positive labels for `unnecessary_complexity` and `introduces_secret`, so their 1.00 rows are
empty statements. What the set does show:

- `unrequested_behavior_change` is the one question that already earns its threshold. It fired
  on `tools.py` (an undisclosed tool-contract change, labeled pushback) and on `smoke.sh` (an
  undisclosed `--user` flag, labeled yes but verdict clean), and stayed under 0.5 on everything
  else. One false positive: `paused.ts` (0.85), a new file inside a large commit whose message is
  truncated at 2 KB before the kill switch is mentioned. Task truncation is a real failure mode
  for big turns.
- `swallows_failure`, v1 wording, scored the two real fail-open cases at 0.26 and 0.27, no
  better than the clean deltas. The v1 text asked about "a failure that previously surfaced",
  which excludes new code that fails open. After broadening the criteria to name defaulted-away
  errors, the same two cases score 0.72 (`paused.ts`) and 0.46 (`isolation.go`) while the highest
  clean delta is 0.34. That is separation, but at 0.85 both are still misses. With n=2 positives
  no threshold should ship; the honest reading is that 0.85 is too high and 0.5 to 0.6 is the
  region to test once Will's labels add more positives.
- Security Nouls produced no false positive above 0.85 (criterion 3's requirement for them).
  `unsafe_input_use` missed the one real case (`workspace.ts`, agent diff paths written without
  containment, 0.35) and `weakens_check` missed `research.ts` (0.23), where the loosened check was
  what the task asked for. `new_external_surface` scored the four requested external surfaces
  at 0.81, 0.58, 0.37, 0.20; all four were legitimately requested by the task, so a block rule on
  this question would fire on clean work. Suggestion: make `new_external_surface` an advise
  rule that names the surface, not a block.
- `tests_proportional` is lenient: six deltas labeled no scored above 0.30. The best threshold on
  this set is 0.45. Per-file judgment of tests is inherently weak; adding `turn_files_changed`
  (every path the turn touched, with line counts) to the state was necessary so the model can
  see sibling test files at all.

**Policy versus verdict.** Of 10 pushback deltas, 2 got a block (both correct) and 8 passed. Of
28 clean deltas, 27 passed and 1 was blocked (`smoke.sh`, on a change the labeler also marked
undisclosed). The misses are the kinds of defect a per-file diff cannot show: a fence that breaks
`stop` because stop carries no profile, a sync that bypasses an acknowledgement gate elsewhere,
a symlink escape past a lexical check. Those need the whole turn or the codebase, not one file.

**Recommendation: continue.** The judgments the tool can make from a per-file diff are made
consistently, quickly, and cheaply. The first-order wins are `unrequested_behavior_change` and
the Scores; `swallows_failure` is promising with revised wording; the security Nouls are safe
(no false blocks) but not yet sensitive. The two open questions from SPEC section 10 that
calibration should answer next, once Will has corrected these labels: whether a whole-turn state
lifts `swallows_failure` and `unrequested_behavior_change` on the misses above, and whether
`unnecessary_complexity` ever fires on real deltas. The last needs positive examples; agent-written
turns during dogfood are the most likely source, since none of the 38 human-reviewed commits here
were labeled disproportionate.

**Threshold suggestions from this set (not shipped; all values in `jev-review.toml` remain
uncalibrated until Will's labels are in):** `swallows_failure_block` 0.85 to 0.60 and an advisory
band at 0.40; `new_external_surface` moved from block to advise at 0.50; `tests_missing_advise`
0.30 to 0.45; leave `unrequested_change_block` at 0.80.
