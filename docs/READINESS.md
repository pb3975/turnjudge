# Readiness against SPEC section 7

Last updated 2026-09-16 by the builder agent. Every checked item points at the file, test, or log
line that proves it. Unchecked items say why and what it would take. Regenerate the evidence with:

```sh
uv run pytest -q                       # tests
uv run jev-review calibrate run        # calibration/report.md (recorded responses reused)
uv run jev-review doctor               # setup and one live request
uv run jev-review feedback x list      # blocks and their marks
```

## Summary

| # | Criterion | Status | Needs Will? |
|---|---|---|---|
| 1 | Tests pass locally and in CI | locally yes; no CI service (no remote) | decision: accept local run, or add a remote |
| 2 | 40 labeled deltas, 3 repos, half pushback, labeled by Will | 38 deltas, 4 repos, 10 pushback, labeled by the builder | yes: correct labels, add pushback cases |
| 3 | Agreement and MAE targets | Scores and security met on the builder set; unnecessary_complexity has no positives; swallows_failure misses at 0.85 | yes: follows from 2 |
| 4 | 10 sessions, 7 of 10 blocks helpful, no stall | 15 sessions, no stall, 0 blocks to mark | yes: sessions on his repos, marks |
| 5 | doctor on a fresh machine from the README | passes here; fresh machine untried | yes, or a scratch VM |
| 6 | Redaction corpus clean; audit log reviewed by Will | corpus clean; builder scan clean | yes: review the audit logs |
| 7 | Plugin installs; /jev-review works | yes | no |

## 1. All tests in section 6 pass in CI and locally

- [x] Locally: `uv run pytest -q` passes (see the run recorded under "Evidence log" below).
  Unit: `tests/test_redact.py` (one test per pattern, 50 secrets and 50 look-alikes),
  `tests/test_delta.py` (untracked, renamed, deleted, binary, over-cap, index untouched),
  `tests/test_policy.py` (every rule at its boundary, every template slot).
  Hook contract: `tests/test_hooks.py` (documented stdin JSON per event, exact stdout and exit code,
  `stop_hook_active=true`, missing mark, no git, garbage stdin, exception path, no key, service
  unavailable, slow service within budget, mode advise/off, SubagentStop advisory, too-large delta,
  withheld files, secret in diff). Loop safety: `test_loop_safety_three_stops_one_block`.
  Offline integration: `tests/test_integration.py` against `calibration/responses/`.
  Live smoke: `tests/test_live.py`, skipped without `JEV_REVIEW_LIVE=1` and a key; passed live on
  2026-09-16. Latency: `calibration/report.md`, "6-file wall-time test".
- [ ] In CI: not met. The repo is private with no remote, so no CI service has run it.
  `scripts/ci.sh` runs the same steps; `.github/workflows/ci.yml` is ready for when a remote exists.
  What it would take: a remote and a key stored as a CI secret, or accepting the local run as CI.

## 2. At least 40 labeled file deltas from three repos, half clean and half pushback, labeled by Will

- [ ] Not met. `calibration/labels.yaml` has 38 deltas from four repos (17 nests, 12
  agentic-sw-factory, 3 qb-harness, 3 billy-blog, plus 3 traced nests deltas), 28 clean and 10
  pushback, and the labels are the builder's, not Will's. Real history from a careful author is
  mostly clean; the pushback cases were found by tracing later "address review" commits back to
  the delta they corrected. What it would take: Will corrects the verdicts and labels in
  `calibration/labels.yaml` (each entry has a `note` with the reasoning) and adds enough
  pushback deltas to reach 20 of 40. Candidates: `uv run jev-review calibrate candidates --repo
  ~/Work/nests --range HEAD`. Agent-written turns from dogfood sessions are the most likely
  source of disproportionate-complexity examples; none of the 38 human-reviewed commits has one.

## 3. Agreement and error targets on that set at shipped thresholds

Measured on the builder-labeled set (`calibration/report.md`, regenerated 2026-09-16); it does not
count until criterion 2 is met.

- [x] Scores: MAE 0.33 / 0.36 / 0.32 / 0.45 / 0.35 levels for behavior, control flow, abstraction,
  maintenance risk, verbosity; all at or under 0.6. Row "Score questions" in the report.
- [x] Security Nouls: zero false positives above 0.85 on 38 deltas ("FP @shipped" column).
- [ ] `unnecessary_complexity` at or above 0.80 agreement: the 1.00 in the report is empty because the
  set has zero positive labels. Not met until positives exist.
- [ ] `swallows_failure` at or above 0.80 agreement: 0.95 overall but both positives are missed at
  0.85 (they score 0.72 and 0.46 after the criteria were broadened; 0.27 and 0.26 under the v1
  wording kept in `calibration/responses-v1/`). The highest clean delta is 0.34. What it would
  take: Will's labels plus more positives, then a threshold in the 0.5 to 0.6 range if the
  separation holds. Not shipped.

## 4. Ten real agent sessions on two of Will's repos, blocks marked, 7 of 10 helpful, no stall

- [ ] Not met. 19 headless agent sessions ran with the hooks live on 2026-09-16 and 17: 5 in this
  repo (through `.claude/settings.json`), 10 in a scratch clone of `~/Work/qb-harness`, and 4 with
  a delta in a scratch clone of `~/Work/nests` (through the installed plugin at local scope; Will's
  own working trees were not touched). Every check completed in under 0.9 s and no session
  stalled. Outcomes: 16 pass, 3 advisories (verbosity once, tests_proportional twice),
  0 blocks. In nests, "skip a host whose lease record cannot be parsed" scored `swallows_failure`
  0.65 and the `--dry-run` flag that skips the high-autonomy confirmation gate scored
  `weakens_check` under threshold; both are the 0.6 to 0.85 band where Will's marks decide. With no blocks there is nothing to mark, so the
  7-of-10 test cannot be evaluated yet. The closest call: the grep task "skip binary files and
  unreadable directories quietly" scored `swallows_failure` 0.84 against a block threshold of 0.85;
  the calibration assessment's suggested 0.60 would have blocked it. Whether that block would have
  been helpful is Will's call. Sessions on Will's own repos and the marks are his to run and give:
  `claude plugin install jev-review@jev-review-local` (after `claude plugin marketplace add
  ~/Work/jev-review`), work as usual, then `jev-review feedback <session-prefix>/<turn>
  helpful|unhelpful` for each block. `jev-review feedback x list` shows the blocks.
  No stall: every hook path exits 0 with a hard exit past the budget
  (`tests/test_hooks.py::test_slow_service_respects_budget`), and the audit log records
  `seconds` per check.

## 5. doctor passes on a fresh machine following only the README

- [ ] Partially. `uv run jev-review doctor` passes on this machine (all checks including one live
  request; output recorded below). A fresh machine has not been tried. What it would take: Will or
  a scratch VM follows README "Install" steps 1 to 3.

## 6. Redaction corpus has zero leaks; dogfood audit log reviewed by Will

- [x] Corpus: `tests/test_redact.py::test_corpus_secret_redacted` (50 secrets, each asserted to be
  absent from the output) and `test_corpus_lookalike_survives` (50 look-alikes unchanged) pass.
  Hook-level: `test_withheld_files_are_named_and_not_sent` and
  `test_secret_in_diff_is_redacted_before_audit` assert the audit log carries no secret.
- [ ] Audit log reviewed by Will: not met. The logs are under
  `~/.local/state/jev-review/jev-review-*/audit/`. The builder scanned them for the home path,
  email, hostname, and key prefixes (zero hits in sent state); Will's review is still required.

## 7. Plugin installs via marketplace add and plugin install; /jev-review works

- [x] `claude plugin marketplace add /home/wam/Work/jev-review` then
  `claude plugin install jev-review@jev-review-local --scope local` succeeded in a scratch repo on
  2026-09-16 (`claude plugin list` shows jev-review@jev-review-local 0.1.0 enabled).
  `claude plugin validate .` passes. `/jev-review` invoked headlessly in that repo ran
  `jev-review explain` through the plugin and printed the answer table (live Jev answers; a
  `try/except Exception: pass` around `os.system` scored `swallows_failure` 0.94 and
  `unsafe_input_use` 0.82). The SessionStart and UserPromptSubmit hooks ran in that session
  (`~/.local/state/jev-review/plugin-test-*/sessions/`).

## Dogfood sessions

Filled in as sessions run. Each row is one audited session on this repo.

| date | repo | session | checks | blocks | advisories | skipped | max seconds | fired rules | block marks |
|---|---|---|---|---|---|---|---|---|---|
| 2026-09-17 | nests | 17a451ef | 1 | 0 | 0 | 0 | 0.45 | - | - |
| 2026-09-17 | qb | 17dd0573 | 1 | 0 | 1 | 0 | 0.67 | tests_proportional | - |
| 2026-09-17 | qb | 256efb75 | 1 | 0 | 0 | 0 | 0.59 | - | - |
| 2026-09-17 | jev-review | 290012df | 1 | 0 | 0 | 0 | 0.48 | - | - |
| 2026-09-17 | qb | 38e774a3 | 1 | 0 | 1 | 0 | 0.56 | tests_proportional | - |
| 2026-09-17 | qb | 402335ab | 1 | 0 | 0 | 0 | 0.46 | - | - |
| 2026-09-17 | nests | 4327693a | 1 | 0 | 0 | 0 | 0.62 | - | - |
| 2026-09-17 | jev-review | 433dbfc9 | 1 | 0 | 1 | 0 | 0.53 | verbosity | - |
| 2026-09-17 | qb | 4ff943e4 | 1 | 0 | 0 | 0 | 0.46 | - | - |
| 2026-09-17 | qb | 6a8cf403 | 1 | 0 | 0 | 0 | 0.53 | - | - |
| 2026-09-17 | qb | 90b4c816 | 1 | 0 | 0 | 0 | 0.52 | - | - |
| 2026-09-17 | jev-review | a9fe7d8e | 1 | 0 | 0 | 0 | 0.50 | - | - |
| 2026-09-17 | qb | c9d3b509 | 1 | 0 | 0 | 0 | 0.59 | - | - |
| 2026-09-17 | nests | c9e99945 | 1 | 0 | 0 | 0 | 0.49 | - | - |
| 2026-09-17 | nests | cf6e180f | 1 | 0 | 0 | 0 | 0.57 | - | - |
| 2026-09-17 | jev-review | d794b3ed | 1 | 0 | 0 | 0 | 0.45 | - | - |
| 2026-09-17 | qb | eb806de3 | 1 | 0 | 0 | 0 | 0.73 | - | - |
| 2026-09-17 | jev-review | eeabdf9a | 1 | 0 | 0 | 0 | 0.65 | - | - |
| 2026-09-17 | qb | fee4d00b | 1 | 0 | 0 | 0 | 0.83 | - | - |

19 sessions, 19 checks, 0 blocks, 3 advisories, 0 skipped, max seconds 0.83

Tasks given to the agent, in order: this repo: percentile tests; scripts/ci.sh; audit subcommand;
robust Store.audit; Azure and Twilio redaction patterns. qb-harness clone: shell timeout; retry
once on connection error; --quiet flag; refuse escaping paths; pluggable provider registry;
turn-limit flag instead of raise; never crash when Ollama is down; grep skips unreadable dirs
quietly; agentlab.toml defaults; "clean up agent.py". nests clone (2026-09-17): reject empty
profile name (no change was needed, so no delta and no check); debug logging in docker(); profile
name helper; skip unparseable lease records; --dry-run for nest agent start. The registry task scored abstraction 3.0
with unnecessary_complexity 0.16, which is the intended reading: the task asked for it. The
"clean up" task scored unrequested_behavior_change 0.23 on a pure refactor.
Regenerate the table with `uv run python scripts/dogfood_table.py`.

## PR reviews (2026-09-17, `explain --range`, live Jev)

Will approved testing across his repos on 2026-09-17. Both PRs were fetched into scratch clones
(his working trees untouched) and reviewed as a commit range with the commit messages as the task.

agentic-sw-factory PR 8 "Add current software factory case studies and rollout model" (8 commits,
7 content files): outcome pass. Every code question sits near zero on YAML and Markdown, which
answers SPEC section 10's last question for content-only turns: the question set does no harm
there but has nothing to say; a reduced set is not needed, skipping is optional.

```
file                                     out         beh   cflow   abstr   maint    verb   unnec   swall   unreq   tests  secret   input  weaken extsurf
content/course.yaml                      pass       1.36    0.00    0.00    0.09    0.03    0.11    0.04    0.10    0.74    0.04    0.03    0.02    0.03
/08-openai-agentic-factory-case-study.md pass       1.97    0.00    0.00    0.05    0.08    0.10    0.04    0.08    0.86    0.03    0.03    0.02    0.03
content/modules/02-anatomy/module.yaml   pass       2.04    0.00    0.00    0.10    0.05    0.12    0.04    0.08    0.79    0.03    0.03    0.02    0.03
ns/lessons/07-crawl-walk-run-adoption.md pass       2.08    0.00    0.01    0.05    0.08    0.11    0.04    0.11    0.86    0.02    0.02    0.02    0.03
ontent/modules/07-operations/module.yaml pass       1.74    0.00    0.00    0.05    0.02    0.11    0.03    0.09    0.79    0.02    0.02    0.02    0.03
eer-openai-agentic-software-factory.yaml pass       1.75    0.00    0.01    0.04    0.13    0.10    0.05    0.07    0.79    0.05    0.02    0.02    0.03
arp-crawl-walk-run-software-factory.yaml pass       1.88    0.00    0.05    0.03    0.06    0.10    0.05    0.09    0.78    0.04    0.02    0.02    0.03

turn outcome: pass
audit: /home/wam/.local/state/jev-review/asf-99a3d97b/audit/2026-09-17.jsonl
```

nests PR 95 "Publish verified fleet bundles and verify Host downloads" (2 commits, 10 files: two
workflows, deploy script, CloudFormation template, a Python manifest tool with tests, a Go test):
outcome pass. `unrequested_behavior_change` sits at 0.5 to 0.7 on the workflow and shell files
because the two commit subjects describe the whole PR, not each file; nothing crossed a threshold.

```
file                                     out         beh   cflow   abstr   maint    verb   unnec   swall   unreq   tests  secret   input  weaken extsurf
.github/workflows/fleet-release.yml      pass       2.76    1.00    0.26    1.38    0.68    0.35    0.17    0.65    0.51    0.04    0.17    0.08    0.62
.github/workflows/image-pipeline.yml     pass       2.09    1.00    0.27    1.07    0.52    0.29    0.09    0.49    0.38    0.04    0.27    0.05    0.18
.gitignore                               pass       0.34    0.01    0.01    0.03    0.78    0.24    0.08    0.52    0.83    0.03    0.09    0.04    0.10
docs/operations/fleet-releases.md        pass       0.68    0.02    0.07    0.39    0.46    0.24    0.13    0.34    0.81    0.04    0.13    0.13    0.12
infra/aws-m4/deploy.sh                   pass       2.41    1.52    0.05    1.40    0.42    0.32    0.15    0.59    0.50    0.03    0.13    0.17    0.10
infra/aws-m4/template.yaml               pass       2.45    0.83    0.24    0.91    0.66    0.27    0.12    0.51    0.66    0.04    0.12    0.05    0.12
ternal/iamcheck/release_template_test.go pass       0.79    1.98    0.31    0.26    0.32    0.21    0.08    0.22    0.92    0.03    0.08    0.06    0.06
scripts/fleet-release/manifest.py        pass       2.44    1.99    1.01    0.91    0.69    0.27    0.09    0.55    0.76    0.03    0.25    0.07    0.04
scripts/fleet-release/manifest_test.py   pass       1.01    1.28    1.00    0.20    0.48    0.21    0.10    0.42    0.93    0.03    0.09    0.07    0.05
scripts/fleet-release/package.sh         pass       2.58    1.74    0.19    1.58    0.87    0.36    0.12    0.70    0.40    0.04    0.19    0.10    0.11

turn outcome: pass
audit: /home/wam/.local/state/jev-review/nests-1a3dfcc4/audit/2026-09-17.jsonl
```

## Evidence log

Command outputs pasted at the time of the last update.

```
$ uv run pytest -q   (2026-09-16T22:03:41-05:00)
........................................................................ [ 97%]
.....                                                                    [100%]

$ JEV_REVIEW_LIVE=1 uv run pytest -q tests/test_live.py
.                                                                        [100%]

$ uv run jev-review doctor
ok   key        key file /home/wam/.config/jev-review/key (mode 0600)
ok   git        git on PATH
ok   repo       repo jev-review
ok   standards  standards: /home/wam/Work/jev-review/STANDARDS.md
ok   state      state dir /home/wam/.local/state/jev-review
ok   config     config: /home/wam/Work/jev-review/jev-review.toml
ok   mode       mode=block subagents=advise timeout=45.0s model=jev-latest
ok   api        reachable (0.34s, model jev-1.13.0)

all checks passed.

$ uv run jev-review calibrate run (summary lines)
Generated 2026-09-16T22:03 from 38 labeled file deltas across 4 repos (agentic-sw-factory, billy-blog, nests, qb-harness). Labels: `calibration/labels.yaml`. Responses: `calibration/responses/`.
Verdict balance: 28 clean, 10 pushback, 0 unmarked.
| behavior_added | 38 | 0.33 | 0.66 | 0.97 | 1.42 | 1.71 | 0.71 |
| verbosity | 38 | 0.35 | 0.74 | 1.00 | 0.13 | 0.38 | 0.54 |
| clean | 27 | 0 | 1 |
| pushback | 8 | 0 | 2 |
- 6-file wall-time test: {'files': 6, 'wall_seconds': 0.52, 'per_request_seconds': [0.47, 0.52, 0.45, 0.43, 0.41, 0.41], 'errors': 0, 'measured_at': '2026-09-16T21:39:03'}

$ bash scripts/ci.sh; echo exit $?
........................................................................ [ 97%]
.....                                                                    [100%]
exit 0
```
