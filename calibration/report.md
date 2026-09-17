# Calibration report

Generated 2026-09-16T21:58 from 38 labeled file deltas across 4 repos (agentic-sw-factory, billy-blog, nests, qb-harness). Labels: `calibration/labels.yaml`. Responses: `calibration/responses/`.

Verdict balance: 28 clean, 10 pushback, 0 unmarked.

## Noul questions

| question | n | shipped thr | agreement @shipped | Brier | best thr | agreement @best | FP @shipped | FN @shipped |
|---|---|---|---|---|---|---|---|---|
| unnecessary_complexity | 38 | 0.80 | 1.00 | 0.048 | 0.70 | 1.00 | 0 | 0 |
| swallows_failure | 38 | 0.85 | 0.95 | 0.038 | 0.60 | 0.97 | 0 | 2 |
| unrequested_behavior_change | 38 | 0.80 | 0.97 | 0.066 | 0.50 | 0.97 | 1 | 0 |
| tests_proportional | 38 | 0.30 | 0.84 | 0.145 | 0.45 | 0.87 | 0 | 6 |
| introduces_secret | 38 | 0.85 | 1.00 | 0.001 | 0.20 | 1.00 | 0 | 0 |
| unsafe_input_use | 38 | 0.85 | 0.97 | 0.026 | 0.20 | 0.97 | 0 | 1 |
| weakens_check | 38 | 0.85 | 0.97 | 0.035 | 0.55 | 0.97 | 0 | 1 |
| new_external_surface | 38 | 0.85 | 0.89 | 0.044 | 0.20 | 0.97 | 0 | 4 |

FP = fired above threshold on a delta labeled no. FN = stayed below on a delta labeled yes. For `tests_proportional` the policy fires when p is at or under the threshold, so FP means 'flagged as missing tests when labeled proportional'.

## Score questions

| question | n | MAE (levels) | within 0.5 | within 1.0 | mean label | mean answer | mean confidence |
|---|---|---|---|---|---|---|---|
| behavior_added | 38 | 0.33 | 0.66 | 0.97 | 1.42 | 1.71 | 0.71 |
| control_flow_added | 38 | 0.36 | 0.66 | 1.00 | 0.97 | 1.30 | 0.82 |
| abstraction_added | 38 | 0.33 | 0.76 | 0.92 | 0.63 | 0.92 | 0.81 |
| maintenance_risk | 38 | 0.45 | 0.50 | 1.00 | 0.71 | 0.97 | 0.63 |
| verbosity | 38 | 0.35 | 0.74 | 1.00 | 0.13 | 0.38 | 0.54 |

## Policy outcome vs verdict

Shipped policy applied to each recorded response, compared with the labeler's overall verdict.

| verdict | pass | advise | block |
|---|---|---|---|
| clean | 27 | 0 | 1 |
| pushback | 8 | 0 | 2 |

Pushback deltas that got at least advise: 0.20.
Clean deltas that passed silently: 0.96. Clean deltas blocked: 1.

## Per-delta answers

| repo | sha | file | verdict | outcome | fired | unnec | swall | unreq | tests | secret | input | weaken | extsurf | beh | cflow | abstr | maint | verb |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nests | 2f4369b | internal/cli/agent.go | clean | pass | - | 0.22 | 0.11 | 0.17 | 0.79 | 0.02 | 0.05 | 0.06 | 0.03 | 1.54 | 1.97 | 1.28 | 1.60 | 0.55 |
| nests | 2f4369b | internal/config/config.go | clean | pass | - | 0.17 | 0.06 | 0.11 | 0.71 | 0.02 | 0.03 | 0.05 | 0.02 | 0.94 | 1.02 | 1.21 | 0.61 | 0.21 |
| nests | 00a4e13 | internal/agent/harness.go | clean | pass | - | 0.18 | 0.06 | 0.09 | 0.60 | 0.02 | 0.04 | 0.51 | 0.02 | 1.04 | 0.68 | 0.10 | 0.69 | 0.20 |
| nests | 00a4e13 | internal/fleet/command.go | clean | pass | - | 0.22 | 0.05 | 0.18 | 0.69 | 0.02 | 0.04 | 0.14 | 0.02 | 1.05 | 0.92 | 1.07 | 0.67 | 0.30 |
| nests | fcedc8f | internal/network/egress.go | clean | pass | - | 0.09 | 0.03 | 0.09 | 0.72 | 0.02 | 0.03 | 0.03 | 0.02 | 1.05 | 1.20 | 0.00 | 0.06 | 0.04 |
| nests | b7fc601 | internal/reconcile/reconcile.go | clean | pass | - | 0.28 | 0.16 | 0.40 | 0.15 | 0.02 | 0.04 | 0.14 | 0.06 | 1.73 | 1.84 | 0.97 | 1.74 | 0.43 |
| nests | 72977cb | nal/runtime/firecracker/firecracker.go | clean | pass | - | 0.18 | 0.22 | 0.16 | 0.48 | 0.02 | 0.19 | 0.06 | 0.04 | 1.40 | 1.30 | 1.03 | 1.05 | 0.17 |
| nests | af5f5dd | nal/runtime/firecracker/firecracker.go | clean | pass | - | 0.24 | 0.08 | 0.15 | 0.76 | 0.02 | 0.06 | 0.09 | 0.04 | 1.01 | 1.12 | 1.00 | 0.29 | 0.13 |
| nests | 78e4df2 | nal/runtime/firecracker/firecracker.go | clean | pass | - | 0.15 | 0.07 | 0.28 | 0.31 | 0.02 | 0.07 | 0.06 | 0.04 | 1.04 | 1.09 | 0.00 | 0.52 | 0.12 |
| nests | 1a8c830 | internal/agent/bedrock.go | clean | pass | - | 0.18 | 0.08 | 0.25 | 0.72 | 0.03 | 0.04 | 0.04 | 0.82 | 2.32 | 2.03 | 1.99 | 1.61 | 0.63 |
| nests | 1a8c830 | infra/aws-m4/deploy.sh | clean | pass | - | 0.24 | 0.12 | 0.47 | 0.58 | 0.04 | 0.10 | 0.09 | 0.13 | 1.97 | 0.41 | 0.02 | 0.55 | 0.28 |
| nests | 64029cc | nal/runtime/firecracker/firecracker.go | clean | pass | - | 0.20 | 0.13 | 0.44 | 0.71 | 0.02 | 0.12 | 0.14 | 0.07 | 1.52 | 1.73 | 0.00 | 1.64 | 0.32 |
| nests | 1a81272 | internal/state/store.go | clean | pass | - | 0.17 | 0.10 | 0.17 | 0.46 | 0.02 | 0.05 | 0.06 | 0.04 | 0.69 | 0.01 | 1.15 | 0.87 | 0.38 |
| nests | 1a81272 | internal/cli/agent.go | clean | pass | - | 0.24 | 0.12 | 0.31 | 0.56 | 0.02 | 0.06 | 0.09 | 0.03 | 2.46 | 1.49 | 1.11 | 1.46 | 0.60 |
| nests | 983e89b | internal/fleet/session.go | clean | pass | - | 0.20 | 0.06 | 0.36 | 0.41 | 0.04 | 0.04 | 0.07 | 0.02 | 1.04 | 0.92 | 0.53 | 0.75 | 0.16 |
| nests | 082e90b | internal/agent/harness.go | pushback | pass | - | 0.09 | 0.06 | 0.06 | 0.76 | 0.02 | 0.04 | 0.03 | 0.02 | 1.08 | 1.04 | 0.00 | 0.50 | 0.14 |
| nests | 082e90b | internal/cli/agent.go | pushback | pass | - | 0.22 | 0.16 | 0.15 | 0.73 | 0.02 | 0.07 | 0.08 | 0.04 | 2.51 | 1.89 | 1.92 | 1.64 | 0.54 |
| agentic-sw-factory | 1d7cf9a | apps/server/src/audit/write.ts | clean | pass | - | 0.18 | 0.12 | 0.18 | 0.74 | 0.02 | 0.09 | 0.05 | 0.03 | 2.24 | 1.99 | 1.50 | 1.35 | 0.62 |
| agentic-sw-factory | 1d7cf9a | apps/server/src/factory/refresh.ts | clean | pass | - | 0.20 | 0.59 | 0.13 | 0.67 | 0.02 | 0.08 | 0.06 | 0.03 | 2.02 | 2.00 | 1.19 | 0.95 | 0.56 |
| agentic-sw-factory | 129ed53 | apps/server/src/factory/refresh.ts | clean | pass | - | 0.13 | 0.05 | 0.13 | 0.37 | 0.02 | 0.08 | 0.04 | 0.02 | 1.06 | 0.00 | 0.00 | 0.19 | 0.35 |
| agentic-sw-factory | 731bf5f | apps/server/src/factory/gate.ts | clean | pass | - | 0.14 | 0.10 | 0.07 | 0.85 | 0.02 | 0.05 | 0.07 | 0.02 | 1.11 | 0.71 | 0.02 | 0.62 | 0.12 |
| agentic-sw-factory | 731bf5f | pps/server/src/services/Maintenance.ts | clean | pass | - | 0.16 | 0.20 | 0.09 | 0.56 | 0.02 | 0.08 | 0.41 | 0.02 | 1.75 | 1.76 | 0.38 | 0.90 | 0.18 |
| agentic-sw-factory | 4d3f9af | apps/web/src/lib/api.ts | clean | pass | - | 0.09 | 0.11 | 0.14 | 0.70 | 0.02 | 0.03 | 0.38 | 0.04 | 1.79 | 0.03 | 0.50 | 0.15 | 0.07 |
| agentic-sw-factory | 4d3f9af | apps/web/src/lib/analytics.ts | pushback | pass | - | 0.21 | 0.11 | 0.08 | 0.85 | 0.02 | 0.03 | 0.10 | 0.23 | 2.06 | 1.93 | 1.14 | 1.07 | 0.47 |
| agentic-sw-factory | 4d3f9af | src/components/learning-state-sync.tsx | clean | pass | - | 0.15 | 0.11 | 0.09 | 0.64 | 0.02 | 0.04 | 0.12 | 0.05 | 2.20 | 1.76 | 1.25 | 1.32 | 0.23 |
| agentic-sw-factory | 3f5a0df | apps/server/src/factory/research.ts | clean | pass | - | 0.16 | 0.15 | 0.15 | 0.80 | 0.03 | 0.14 | 0.24 | 0.32 | 2.51 | 1.93 | 2.30 | 1.71 | 0.45 |
| agentic-sw-factory | 681795e | blueprints/adapter/src/workspace.ts | pushback | pass | - | 0.17 | 0.08 | 0.12 | 0.57 | 0.03 | 0.40 | 0.03 | 0.06 | 2.15 | 1.81 | 1.27 | 1.00 | 0.22 |
| agentic-sw-factory | 3218ec0 | apps/server/src/http/static.ts | pushback | pass | - | 0.17 | 0.48 | 0.09 | 0.48 | 0.03 | 0.09 | 0.06 | 0.07 | 2.11 | 2.07 | 1.83 | 1.17 | 0.56 |
| qb-harness | 57a64d1 | src/agentlab/agent.py | clean | pass | - | 0.25 | 0.08 | 0.44 | 0.62 | 0.18 | 0.12 | 0.07 | 0.48 | 2.13 | 1.53 | 1.45 | 1.07 | 0.35 |
| qb-harness | 57a64d1 | src/agentlab/tools.py | pushback | block | unrequested_behavior_change | 0.34 | 0.26 | 0.83 | 0.46 | 0.02 | 0.65 | 0.05 | 0.05 | 1.48 | 0.98 | 0.09 | 0.60 | 0.80 |
| qb-harness | 57a64d1 | src/agentlab/cli.py | clean | pass | - | 0.23 | 0.10 | 0.30 | 0.52 | 0.02 | 0.05 | 0.05 | 0.13 | 2.22 | 0.67 | 0.39 | 0.94 | 0.22 |
| billy-blog | 34ad520 | src/lib/server/runtime.ts | clean | pass | - | 0.19 | 0.12 | 0.07 | 0.25 | 0.02 | 0.04 | 0.05 | 0.04 | 1.40 | 1.14 | 0.98 | 1.29 | 0.48 |
| billy-blog | 34ad520 | src/lib/server/db.ts | clean | pass | - | 0.10 | 0.09 | 0.07 | 0.41 | 0.02 | 0.06 | 0.07 | 0.05 | 1.00 | 0.10 | 0.00 | 0.16 | 0.01 |
| billy-blog | 34ad520 | scripts/smoke.sh | clean | block | unrequested_behavior_change | 0.19 | 0.15 | 0.80 | 0.71 | 0.03 | 0.08 | 0.11 | 0.11 | 1.26 | 1.44 | 0.01 | 0.60 | 0.58 |
| nests | 4060b18 | internal/agent/isolation.go | pushback | pass | - | 0.16 | 0.46 | 0.18 | 0.77 | 0.02 | 0.07 | 0.06 | 0.16 | 2.53 | 2.01 | 1.15 | 1.64 | 0.66 |
| nests | d0ea812 | internal/agent/linux.go | pushback | pass | - | 0.20 | 0.11 | 0.18 | 0.61 | 0.03 | 0.06 | 0.05 | 0.45 | 2.57 | 1.96 | 1.73 | 1.85 | 0.58 |
| agentic-sw-factory | c083057 | apps/server/src/factory/paused.ts | pushback | block | unrequested_behavior_change | 0.68 | 0.72 | 0.86 | 0.32 | 0.02 | 0.06 | 0.05 | 0.05 | 1.98 | 1.15 | 1.51 | 0.60 | 0.88 |
| nests | 020cedf | internal/agent/guest_harness.go | pushback | pass | - | 0.16 | 0.17 | 0.22 | 0.75 | 0.02 | 0.06 | 0.05 | 0.06 | 2.88 | 1.96 | 2.89 | 1.53 | 0.78 |

## Cost and latency

- Requests: 38; input tokens: 237478; output tokens: 8816; billing_units: not returned by the API (SDK 0.6.0 note).
- Per-request latency: median 0.19 s, max 0.53 s, mean input tokens 6249.
- 6-file wall-time test: {'files': 6, 'wall_seconds': 0.52, 'per_request_seconds': [0.47, 0.52, 0.45, 0.43, 0.41, 0.41], 'errors': 0, 'measured_at': '2026-09-16T21:39:03'}

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

**Threshold suggestions from this set (not shipped; all values in `jev-review.toml` remain
uncalibrated until Will's labels are in):** `swallows_failure_block` 0.85 to 0.60 and an advisory
band at 0.40; `new_external_surface` moved from block to advise at 0.50; `tests_missing_advise`
0.30 to 0.45; leave `unrequested_change_block` at 0.80.

**Whole-turn state experiment (SPEC section 10).** Run after Phase 0; details in
`calibration/experiments/README.md`. Sending every file of a commit in one request lowered
`swallows_failure` and `unrequested_behavior_change` on the positives (0.72 to 0.36, 0.83 to 0.68)
without lowering the clean deltas by more, and the 60 KB cap truncated large commits. Per-file
stays the unit for v1.
