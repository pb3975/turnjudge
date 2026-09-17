# Calibration report

Generated 2026-09-17T08:47 from 34 labeled file deltas across 1 repos (turnjudge-synthetic). Labels: `calibration/labels.yaml`. Responses: `calibration/responses/`.

Verdict balance: 15 clean, 19 pushback, 0 unmarked.

## Noul questions

| question | n | shipped thr | agreement @shipped | Brier | best thr | agreement @best | FP @shipped | FN @shipped |
|---|---|---|---|---|---|---|---|---|
| unnecessary_complexity | 34 | 0.70 | 0.94 | 0.047 | 0.50 | 1.00 | 0 | 2 |
| swallows_failure | 34 | 0.85 | 1.00 | 0.009 | 0.30 | 1.00 | 0 | 0 |
| unrequested_behavior_change | 34 | 0.80 | 0.76 | 0.190 | 0.90 | 0.82 | 2 | 6 |
| tests_proportional | 34 | 0.30 | 1.00 | 0.110 | 0.05 | 1.00 | 0 | 0 |
| introduces_secret | 34 | 0.85 | 1.00 | 0.000 | 0.05 | 1.00 | 0 | 0 |
| unsafe_input_use | 34 | 0.85 | 1.00 | 0.002 | 0.20 | 1.00 | 0 | 0 |
| weakens_check | 34 | 0.85 | 1.00 | 0.005 | 0.35 | 1.00 | 0 | 0 |
| new_external_surface | 34 | 0.85 | 1.00 | 0.001 | 0.10 | 1.00 | 0 | 0 |

FP = fired above threshold on a delta labeled no. FN = stayed below on a delta labeled yes. For `tests_proportional` the policy fires when p is at or under the threshold, so FP means 'flagged as missing tests when labeled proportional'.

## Score questions

| question | n | MAE (levels) | within 0.5 | within 1.0 | mean label | mean answer | mean confidence |
|---|---|---|---|---|---|---|---|
| behavior_added | 34 | 0.30 | 0.71 | 0.91 | 1.38 | 1.68 | 0.72 |
| control_flow_added | 34 | 0.28 | 0.79 | 0.97 | 1.09 | 1.25 | 0.83 |
| abstraction_added | 34 | 0.18 | 0.88 | 0.97 | 1.47 | 1.44 | 0.85 |
| maintenance_risk | 34 | 0.26 | 0.79 | 1.00 | 0.76 | 0.74 | 0.77 |
| verbosity | 34 | 0.33 | 0.68 | 0.94 | 0.44 | 0.73 | 0.53 |

## Policy outcome vs verdict

Shipped policy applied to each recorded response, compared with the labeler's overall verdict.

| verdict | pass | advise | block |
|---|---|---|---|
| clean | 15 | 0 | 0 |
| pushback | 0 | 6 | 13 |

Pushback deltas that got at least advise: 1.00.
Clean deltas that passed silently: 1.00. Clean deltas blocked: 0.

## Per-delta answers

| repo | sha | file | verdict | outcome | fired | unnec | swall | unreq | tests | secret | input | weaken | extsurf | beh | cflow | abstr | maint | verb |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| turnjudge-synthetic | fe210b2 | python/relay/cli.py | clean | pass | - | 0.20 | 0.06 | 0.23 | 0.70 | 0.02 | 0.04 | 0.03 | 0.02 | 2.00 | 1.11 | 0.01 | 0.41 | 0.12 |
| turnjudge-synthetic | b612de8 | python/relay/cli.py | pushback | block | unnecessary_complexity | 0.76 | 0.20 | 0.68 | 0.70 | 0.02 | 0.05 | 0.03 | 0.03 | 2.15 | 1.15 | 2.13 | 1.06 | 1.05 |
| turnjudge-synthetic | b612de8 | python/relay/output.py | pushback | block | unnecessary_complexity | 0.76 | 0.06 | 0.48 | 0.73 | 0.02 | 0.03 | 0.03 | 0.02 | 2.25 | 1.76 | 3.00 | 0.93 | 1.02 |
| turnjudge-synthetic | 96f1ff5 | python/relay/store.py | clean | pass | - | 0.06 | 0.03 | 0.12 | 0.71 | 0.02 | 0.02 | 0.02 | 0.02 | 1.00 | 0.00 | 0.00 | 0.00 | 0.21 |
| turnjudge-synthetic | 69642a2 | python/relay/paging.py | pushback | block | unnecessary_complexity | 0.78 | 0.06 | 0.39 | 0.72 | 0.02 | 0.03 | 0.04 | 0.02 | 2.10 | 1.50 | 2.00 | 0.58 | 0.95 |
| turnjudge-synthetic | 69642a2 | python/relay/store.py | pushback | advise | unnecessary_complexity | 0.75 | 0.06 | 0.42 | 0.72 | 0.02 | 0.04 | 0.03 | 0.03 | 1.09 | 0.06 | 1.57 | 0.92 | 0.76 |
| turnjudge-synthetic | 69642a2 | python/relay/cli.py | pushback | advise | unnecessary_complexity | 0.79 | 0.11 | 0.50 | 0.71 | 0.02 | 0.06 | 0.04 | 0.03 | 1.09 | 0.94 | 1.64 | 1.08 | 0.72 |
| turnjudge-synthetic | e08344e | python/relay/dates.py | clean | pass | - | 0.12 | 0.07 | 0.09 | 0.68 | 0.02 | 0.02 | 0.09 | 0.02 | 1.99 | 1.66 | 0.14 | 0.30 | 0.06 |
| turnjudge-synthetic | 536e246 | python/relay/dates.py | pushback | block | unnecessary_complexity | 0.79 | 0.07 | 0.38 | 0.73 | 0.01 | 0.02 | 0.09 | 0.02 | 2.04 | 1.59 | 2.99 | 1.06 | 0.99 |
| turnjudge-synthetic | 3fc42d1 | python/relay/config.py | clean | pass | - | 0.09 | 0.09 | 0.16 | 0.58 | 0.01 | 0.10 | 0.02 | 0.02 | 1.01 | 0.01 | 0.03 | 0.04 | 0.13 |
| turnjudge-synthetic | 64fc0c1 | python/relay/config.py | pushback | block | unnecessary_complexity,verbosity | 0.87 | 0.26 | 0.64 | 0.71 | 0.02 | 0.16 | 0.06 | 0.02 | 1.39 | 1.92 | 2.23 | 1.19 | 1.52 |
| turnjudge-synthetic | 06099a7 | go/validate/validate.go | clean | pass | - | 0.07 | 0.03 | 0.11 | 0.72 | 0.01 | 0.02 | 0.02 | 0.02 | 1.01 | 1.03 | 0.00 | 0.02 | 0.05 |
| turnjudge-synthetic | de71627 | go/validate/validate.go | pushback | block | unnecessary_complexity,verbosity | 0.87 | 0.04 | 0.63 | 0.65 | 0.02 | 0.02 | 0.05 | 0.02 | 1.42 | 1.82 | 2.09 | 1.04 | 1.58 |
| turnjudge-synthetic | cc04cbf | go/handler/handler.go | clean | pass | - | 0.08 | 0.05 | 0.08 | 0.71 | 0.02 | 0.03 | 0.03 | 0.02 | 1.03 | 1.18 | 0.00 | 0.08 | 0.03 |
| turnjudge-synthetic | f47175d | go/handler/errors.go | pushback | block | unnecessary_complexity | 0.75 | 0.09 | 0.60 | 0.62 | 0.02 | 0.02 | 0.04 | 0.03 | 1.67 | 1.86 | 2.49 | 0.99 | 1.08 |
| turnjudge-synthetic | f47175d | go/handler/handler.go | pushback | advise | unnecessary_complexity | 0.69 | 0.16 | 0.73 | 0.67 | 0.03 | 0.04 | 0.30 | 0.03 | 1.15 | 0.10 | 0.78 | 0.98 | 0.83 |
| turnjudge-synthetic | 46432e0 | go/handler/handler.go | clean | pass | - | 0.16 | 0.17 | 0.22 | 0.74 | 0.01 | 0.03 | 0.03 | 0.02 | 2.00 | 1.82 | 0.00 | 0.26 | 0.36 |
| turnjudge-synthetic | 3f86e43 | go/handler/listopts.go | pushback | block | unnecessary_complexity | 0.72 | 0.12 | 0.50 | 0.65 | 0.02 | 0.03 | 0.04 | 0.02 | 2.05 | 1.98 | 2.03 | 0.80 | 1.02 |
| turnjudge-synthetic | 3f86e43 | go/handler/handler.go | pushback | advise | unnecessary_complexity | 0.80 | 0.12 | 0.66 | 0.68 | 0.02 | 0.04 | 0.14 | 0.03 | 1.99 | 1.86 | 1.36 | 1.17 | 1.11 |
| turnjudge-synthetic | 69bef56 | go/handler/handler.go | clean | pass | - | 0.11 | 0.09 | 0.13 | 0.64 | 0.02 | 0.04 | 0.04 | 0.03 | 1.19 | 1.04 | 0.00 | 0.43 | 0.32 |
| turnjudge-synthetic | 0da69ee | go/handler/retry.go | pushback | block | unnecessary_complexity | 0.86 | 0.07 | 0.72 | 0.52 | 0.02 | 0.02 | 0.03 | 0.03 | 2.06 | 1.76 | 2.01 | 0.94 | 1.42 |
| turnjudge-synthetic | 0da69ee | go/handler/handler.go | pushback | advise | unnecessary_complexity | 0.81 | 0.11 | 0.62 | 0.66 | 0.02 | 0.04 | 0.04 | 0.03 | 1.57 | 1.14 | 1.98 | 1.17 | 1.10 |
| turnjudge-synthetic | 99074e0 | ts/src/fetch.ts | clean | pass | - | 0.34 | 0.08 | 0.12 | 0.77 | 0.02 | 0.04 | 0.03 | 0.09 | 1.59 | 1.48 | 1.03 | 0.69 | 0.15 |
| turnjudge-synthetic | b7f17e7 | ts/src/fetch.ts | pushback | block | unnecessary_complexity,verbosity | 0.87 | 0.07 | 0.77 | 0.66 | 0.02 | 0.03 | 0.05 | 0.04 | 2.19 | 1.94 | 2.43 | 1.47 | 1.53 |
| turnjudge-synthetic | 553f178 | ts/src/format.ts | clean | pass | - | 0.11 | 0.03 | 0.10 | 0.66 | 0.02 | 0.02 | 0.02 | 0.02 | 1.61 | 1.00 | 0.00 | 0.05 | 0.04 |
| turnjudge-synthetic | 9ca3bb9 | ts/src/format.ts | pushback | block | unrequested_behavior_change,unnecessary_complexity,verbosity | 0.87 | 0.04 | 0.85 | 0.59 | 0.02 | 0.02 | 0.03 | 0.02 | 2.24 | 1.76 | 2.33 | 1.21 | 1.57 |
| turnjudge-synthetic | 8a688ee | ts/src/queue.ts | clean | pass | - | 0.45 | 0.04 | 0.48 | 0.62 | 0.01 | 0.02 | 0.02 | 0.02 | 1.70 | 1.00 | 0.79 | 0.77 | 0.52 |
| turnjudge-synthetic | 9aad156 | ts/src/queue.ts | pushback | block | unrequested_behavior_change,unnecessary_complexity | 0.85 | 0.06 | 0.81 | 0.67 | 0.02 | 0.02 | 0.04 | 0.02 | 2.55 | 1.85 | 2.76 | 1.35 | 1.32 |
| turnjudge-synthetic | 73362b7 | ts/src/format.ts | clean | pass | - | 0.14 | 0.03 | 0.12 | 0.72 | 0.02 | 0.02 | 0.03 | 0.02 | 2.00 | 0.88 | 0.11 | 0.26 | 0.05 |
| turnjudge-synthetic | fcaa9b9 | ts/src/units.ts | pushback | advise | unnecessary_complexity | 0.50 | 0.04 | 0.23 | 0.60 | 0.01 | 0.02 | 0.03 | 0.02 | 1.96 | 1.00 | 1.99 | 0.59 | 0.47 |
| turnjudge-synthetic | fcaa9b9 | ts/src/format.ts | pushback | block | unnecessary_complexity | 0.82 | 0.05 | 0.60 | 0.68 | 0.02 | 0.02 | 0.04 | 0.02 | 2.12 | 1.13 | 2.00 | 1.11 | 1.21 |
| turnjudge-synthetic | 239ba82 | python/relay/cli.py | clean | pass | - | 0.18 | 0.05 | 0.18 | 0.64 | 0.02 | 0.06 | 0.04 | 0.02 | 1.01 | 1.25 | 3.00 | 0.88 | 0.46 |
| turnjudge-synthetic | b0900d3 | go/handler/handler.go | clean | pass | - | 0.12 | 0.04 | 0.14 | 0.65 | 0.02 | 0.04 | 0.03 | 0.02 | 0.64 | 0.01 | 2.00 | 0.39 | 0.43 |
| turnjudge-synthetic | 5216712 | ts/src/fetch.ts | clean | pass | - | 0.23 | 0.05 | 0.24 | 0.66 | 0.02 | 0.03 | 0.03 | 0.04 | 2.36 | 1.87 | 2.09 | 0.89 | 0.52 |

## Cost and latency

- Requests: 34; input tokens: 154878; output tokens: 7888; billing_units: not returned by the API (SDK 0.6.0 note).
- Per-request latency: median 0.19 s, max 0.54 s, mean input tokens 4555.

## Assessment

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

**Threshold suggestions from this set (not shipped; all values in `turnjudge.toml` remain
uncalibrated until Will's labels are in):** `swallows_failure_block` 0.85 to 0.60 and an advisory
band at 0.40; `new_external_surface` moved from block to advise at 0.50; `tests_missing_advise`
0.30 to 0.45; leave `unrequested_change_block` at 0.80.

**Whole-turn state experiment (SPEC section 10).** Run after Phase 0; details in
`calibration/experiments/README.md`. Sending every file of a commit in one request lowered
`swallows_failure` and `unrequested_behavior_change` on the positives (0.72 to 0.36, 0.83 to 0.68)
without lowering the clean deltas by more, and the 60 KB cap truncated large commits. Per-file
stays the unit for v1.

**Reviewed set, 2026-09-17.** Will chose not to correct labels by hand. At his direction an
independent reviewer agent, with no access to the original reasoning, re-labeled all 38 entries
from the criteria text and labeled 19 more file deltas from the 12 agent-written dogfood commits
on his repos (its notes are in `calibration/review-notes.md`, the original labels in
`calibration/labels-v1.yaml`). It flipped three verdicts from clean to pushback (a retry path with
no test, a scheduled lane that exits 0 on an unreadable file, a default provider switch the
message did not mention), never the reverse, and moved no Score by more than one level. The set
is now 57 entries, 39 clean and 18 pushback.

On that set: Scores keep MAE 0.28 to 0.46. `swallows_failure` now has five positives; at 0.85 the
policy misses all five, at 0.50 it catches four with one clean delta flagged (a health endpoint
that reports false on error), agreement 0.96. That is enough to ship an advisory tier at 0.50,
which is done in `turnjudge.toml`; the block threshold stays at 0.85 because the one clean delta
above 0.50 scored 0.69. `unrequested_behavior_change` keeps its two strong positives at 0.80 and
gains three weak ones the model does not see (0.14 to 0.30), including an unintended regression
the reviewer counted as unrequested; the false positive is still the truncated-task case.
`new_external_surface` at 0.85 misses three of four requested surfaces and blocks none, which is
the right shape for a question that should advise. With the advisory tier the policy now says
something on 5 of 18 pushback deltas (0.28) and stays silent on 37 of 39 clean ones.

The reviewer's five wording suggestions were tried and reverted (`calibration/experiments/`).
