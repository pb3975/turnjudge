# Readiness against SPEC section 7

Last updated 2026-09-16 by the builder agent. Every checked item points at the file, test, or log
line that proves it. Unchecked items say why and what it would take. Regenerate the evidence with:

```sh
uv run pytest -q                       # tests
uv run turnjudge calibrate run        # calibration/report.md (recorded responses reused)
uv run turnjudge doctor               # setup and one live request
uv run turnjudge feedback x list      # blocks and their marks
```

## Summary

| # | Criterion | Status | Needs Will? |
|---|---|---|---|
| 1 | Tests pass locally and in CI | locally yes; no CI service (no remote) | decision: accept local run, or add a remote |
| 2 | 40 labeled deltas, 3 repos, half pushback, labeled by Will | 57 deltas, 4 repos, 18 pushback, labeled by two agents at Will's direction | Will's call whether that counts; 12 more pushback cases for half |
| 3 | Agreement and MAE targets | Scores, security, and swallows_failure (advisory tier) met on the reviewed set; unnecessary_complexity has no positives | needs a real disproportionate-complexity example |
| 4 | 10 sessions, 7 of 10 blocks helpful, no stall | 32 sessions incl. 12 on his repos, no stall, 1 block to mark | yes: mark the block; decide on the 0.6 band |
| 5 | doctor on a fresh machine from the README | passes here; fresh machine untried | yes, or a scratch VM |
| 6 | Redaction corpus clean; audit log reviewed by Will | corpus clean; builder scan clean | yes: review the audit logs |
| 7 | Plugin installs; /turnjudge works | yes | no |

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
  Live smoke: `tests/test_live.py`, skipped without `TURNJUDGE_LIVE=1` and a key; passed live on
  2026-09-16. Latency: `calibration/report.md`, "6-file wall-time test".
- [ ] In CI: not met. The repo is private with no remote, so no CI service has run it.
  `scripts/ci.sh` runs the same steps; `.github/workflows/ci.yml` is ready for when a remote exists.
  What it would take: a remote and a key stored as a CI secret, or accepting the local run as CI.

## 2. At least 40 labeled file deltas from three repos, half clean and half pushback, labeled by Will

- [ ] Partially met, with a substitution Will chose. `calibration/labels.yaml` has 57 file deltas
  from four repos (nests, agentic-sw-factory, qb-harness, billy-blog): 38 from human commits and
  19 from the agent-written dogfood commits on his repos. 39 are clean and 18 pushback (32
  percent, short of half). On 2026-09-17 Will said he rarely reads the code and asked for a fresh
  agent to answer the label questions instead of him; an independent reviewer agent re-labeled
  every entry from the criteria text alone (`calibration/review-notes.md`; the builder's originals
  are `calibration/labels-v1.yaml`). So the labels are two agents' judgment reconciled, not Will's.
  What it would take to meet the letter of the criterion: Will corrects any entry he disagrees
  with, and about 12 more pushback deltas are added. What it would take to meet its spirit: Will
  marks blocks and advisories from his own sessions (criterion 4), which is the same judgment
  applied where it costs him nothing.

## 3. Agreement and error targets on that set at shipped thresholds

Measured on the reviewed 57-entry set (`calibration/report.md`, regenerated 2026-09-17).

- [x] Scores: MAE 0.29 / 0.33 / 0.32 / 0.45 / 0.32 levels for behavior, control flow,
  abstraction, maintenance risk, verbosity; all at or under 0.6.
- [x] Security Nouls: zero false positives above 0.85 on 57 deltas.
- [ ] `unnecessary_complexity` at or above 0.80 agreement: 1.00 but the set still has zero positive
  labels, including across 19 agent-written deltas. Not met until a positive exists.
- [x] `swallows_failure` at or above 0.80 agreement: 0.91 at the 0.85 block threshold, 0.96 at the
  new 0.50 advisory threshold (4 of 5 positives, 1 clean flagged). The advisory tier shipped in
  `turnjudge.toml` on 2026-09-17 with that evidence; the block threshold is unchanged. A wording
  revision was tried and reverted (`calibration/experiments/README.md`).

## 4. Ten real agent sessions on two of Will's repos, blocks marked, 7 of 10 helpful, no stall

- [ ] Partially met. Will approved sessions on his own repos on 2026-09-17. 12 headless agent
  sessions then ran in git worktrees of nests, agentic-sw-factory, qb-harness, and billy-blog
  (branch `turnjudge/dogfood` in each, one commit per session, his checked-out trees untouched),
  on top of 19 earlier sessions in this repo and in scratch clones, and one scripted session on a
  demo repo. That is 32 sessions with the hooks live: 31 pass or advise, 1 block, no stall, every
  check under 0.9 s including an 8-file turn. The one block is the demo-repo capture (a task that
  asked for a script to always exit 0; `swallows_failure` 0.96; the agent defended the change and
  offered `sys.exit(1)`). It is listed by `turnjudge feedback x list` and is the only block Will
  can mark so far. The 7-of-10 test cannot be evaluated with one block. Across the 12 sessions on
  his repos, every task that asked for a skip, a fallback, or a "never crash" landed between 0.53
  and 0.67 on `swallows_failure`, under the 0.85 block threshold; the calibration assessment's
  suggested 0.60 would have blocked several of them. Whether those blocks would be helpful is the
  question his marks answer. To review the agent's work: `git log turnjudge/dogfood` in each repo;
  delete the branch and worktree when done (`git worktree remove <repo>-turnjudge`).
  Sessions on Will's own repos and the marks are his to run and give:
  `claude plugin install turnjudge@turnjudge-local` (after `claude plugin marketplace add
  ~/Work/turnjudge`), work as usual, then `turnjudge feedback <session-prefix>/<turn>
  helpful|unhelpful` for each block. `turnjudge feedback x list` shows the blocks.
  No stall: every hook path exits 0 with a hard exit past the budget
  (`tests/test_hooks.py::test_slow_service_respects_budget`), and the audit log records
  `seconds` per check.

## 5. doctor passes on a fresh machine following only the README

- [ ] Partially. `uv run turnjudge doctor` passes on this machine (all checks including one live
  request; output recorded below). A fresh machine has not been tried. What it would take: Will or
  a scratch VM follows README "Install" steps 1 to 3.

## 6. Redaction corpus has zero leaks; dogfood audit log reviewed by Will

- [x] Corpus: `tests/test_redact.py::test_corpus_secret_redacted` (50 secrets, each asserted to be
  absent from the output) and `test_corpus_lookalike_survives` (50 look-alikes unchanged) pass.
  Hook-level: `test_withheld_files_are_named_and_not_sent` and
  `test_secret_in_diff_is_redacted_before_audit` assert the audit log carries no secret.
- [ ] Audit log reviewed by Will: not met. The logs are under
  `~/.local/state/turnjudge/turnjudge-*/audit/`. The builder scanned them for the home path,
  email, hostname, and key prefixes (zero hits in sent state); Will's review is still required.

## 7. Plugin installs via marketplace add and plugin install; /turnjudge works

- [x] `claude plugin marketplace add /home/wam/Work/turnjudge` then
  `claude plugin install turnjudge@turnjudge-local --scope local` succeeded in a scratch repo on
  2026-09-16 (`claude plugin list` shows turnjudge@turnjudge-local 0.1.0 enabled).
  `claude plugin validate .` passes. `/turnjudge` invoked headlessly in that repo ran
  `turnjudge explain` through the plugin and printed the answer table (live Jev answers; a
  `try/except Exception: pass` around `os.system` scored `swallows_failure` 0.94 and
  `unsafe_input_use` 0.82). The SessionStart and UserPromptSubmit hooks ran in that session
  (`~/.local/state/turnjudge/plugin-test-*/sessions/`).

## Dogfood sessions

Filled in as sessions run. Each row is one audited session on this repo.

| date | repo | session | checks | blocks | advisories | skipped | max seconds | fired rules | block marks |
|---|---|---|---|---|---|---|---|---|---|
| 2026-09-17 | nests-turnjudge | 033b9829 | 1 | 0 | 0 | 0 | 0.55 | - | - |
| 2026-09-17 | nests | 17a451ef | 1 | 0 | 0 | 0 | 0.45 | - | - |
| 2026-09-17 | qb | 17dd0573 | 1 | 0 | 1 | 0 | 0.67 | tests_proportional | - |
| 2026-09-17 | qb | 256efb75 | 1 | 0 | 0 | 0 | 0.59 | - | - |
| 2026-09-17 | jev-review | 290012df | 1 | 0 | 0 | 0 | 0.48 | - | - |
| 2026-09-17 | qb-harness-turnjudge | 29ad0dd6 | 1 | 0 | 0 | 0 | 0.50 | - | - |
| 2026-09-17 | qb | 38e774a3 | 1 | 0 | 1 | 0 | 0.56 | tests_proportional | - |
| 2026-09-17 | qb | 402335ab | 1 | 0 | 0 | 0 | 0.46 | - | - |
| 2026-09-17 | agentic-sw-factory-turnjudge | 40ead851 | 1 | 0 | 0 | 0 | 0.49 | - | - |
| 2026-09-17 | nests | 4327693a | 1 | 0 | 0 | 0 | 0.62 | - | - |
| 2026-09-17 | jev-review | 433dbfc9 | 1 | 0 | 1 | 0 | 0.53 | verbosity | - |
| 2026-09-17 | billy-blog-turnjudge | 47c76f3e | 1 | 0 | 0 | 0 | 0.81 | - | - |
| 2026-09-17 | qb | 4ff943e4 | 1 | 0 | 0 | 0 | 0.46 | - | - |
| 2026-09-17 | agentic-sw-factory-turnjudge | 63f42ee9 | 1 | 0 | 0 | 0 | 0.55 | - | - |
| 2026-09-17 | qb-harness-turnjudge | 64b18411 | 1 | 0 | 0 | 0 | 0.44 | - | - |
| 2026-09-17 | agentic-sw-factory-turnjudge | 64b7f78c | 1 | 0 | 0 | 0 | 0.56 | - | - |
| 2026-09-17 | qb | 6a8cf403 | 1 | 0 | 0 | 0 | 0.53 | - | - |
| 2026-09-17 | demo | 6e205233 | 1 | 1 | 0 | 0 | 0.48 | swallows_failure | unmarked |
| 2026-09-17 | billy-blog-turnjudge | 88c1c84d | 1 | 0 | 0 | 0 | 0.45 | - | - |
| 2026-09-17 | qb | 90b4c816 | 1 | 0 | 0 | 0 | 0.52 | - | - |
| 2026-09-17 | nests-turnjudge | a8f93d55 | 1 | 0 | 0 | 0 | 0.76 | - | - |
| 2026-09-17 | jev-review | a9fe7d8e | 1 | 0 | 0 | 0 | 0.50 | - | - |
| 2026-09-17 | qb | c9d3b509 | 1 | 0 | 0 | 0 | 0.59 | - | - |
| 2026-09-17 | nests | c9e99945 | 1 | 0 | 0 | 0 | 0.49 | - | - |
| 2026-09-17 | billy-blog-turnjudge | ce51c7df | 1 | 0 | 0 | 0 | 0.56 | - | - |
| 2026-09-17 | nests | cf6e180f | 1 | 0 | 0 | 0 | 0.57 | - | - |
| 2026-09-17 | jev-review | d794b3ed | 1 | 0 | 0 | 0 | 0.45 | - | - |
| 2026-09-17 | nests-turnjudge | d8bb07bd | 1 | 0 | 0 | 0 | 0.55 | - | - |
| 2026-09-17 | qb-harness-turnjudge | e45c3669 | 1 | 0 | 0 | 0 | 0.58 | - | - |
| 2026-09-17 | qb | eb806de3 | 1 | 0 | 0 | 0 | 0.73 | - | - |
| 2026-09-17 | jev-review | eeabdf9a | 1 | 0 | 0 | 0 | 0.65 | - | - |
| 2026-09-17 | qb | fee4d00b | 1 | 0 | 0 | 0 | 0.83 | - | - |

32 sessions, 32 checks, 1 blocks, 3 advisories, 0 skipped, max seconds 0.83

Tasks given to the agent, in order: this repo: percentile tests; scripts/ci.sh; audit subcommand;
robust Store.audit; Azure and Twilio redaction patterns. qb-harness clone: shell timeout; retry
once on connection error; --quiet flag; refuse escaping paths; pluggable provider registry;
turn-limit flag instead of raise; never crash when Ollama is down; grep skips unreadable dirs
quietly; agentlab.toml defaults; "clean up agent.py". nests clone (2026-09-17): reject empty
profile name (no change was needed, so no delta and no check); debug logging in docker(); profile
name helper; skip unparseable lease records; --dry-run for nest agent start. Will's repos
(worktrees, 2026-09-17): nests: github_pat_ redaction; status survives probe timeout; warn on
unknown YAML keys. agentic-sw-factory: 2 MB fetch cap; audit continues past one failed fetch;
--json for academy audit. qb-harness: combined output cap (first attempt got an empty prompt and
did nothing; rerun); run log; grep skips .git and node_modules. billy-blog: ingest skips EACCES
files; /api/health; HEIC thumbnail placeholder. One session in agentic-sw-factory was killed
mid-run when its full vitest suite exhausted memory; its worktree was reset and it was rerun with
an instruction to run only the changed test file. The registry task scored abstraction 3.0
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
audit: /home/wam/.local/state/turnjudge/asf-99a3d97b/audit/2026-09-17.jsonl
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
audit: /home/wam/.local/state/turnjudge/nests-1a3dfcc4/audit/2026-09-17.jsonl
```

## Evidence log

Command outputs pasted at the time of the last update.

```
$ uv run pytest -q   (2026-09-16T22:03:41-05:00)
........................................................................ [ 97%]
.....                                                                    [100%]

$ TURNJUDGE_LIVE=1 uv run pytest -q tests/test_live.py
.                                                                        [100%]

$ uv run turnjudge doctor
ok   key        key file /home/wam/.config/turnjudge/key (mode 0600)
ok   git        git on PATH
ok   repo       repo turnjudge
ok   standards  standards: /home/wam/Work/turnjudge/STANDARDS.md
ok   state      state dir /home/wam/.local/state/turnjudge
ok   config     config: /home/wam/Work/turnjudge/turnjudge.toml
ok   mode       mode=block subagents=advise timeout=45.0s model=jev-latest
ok   api        reachable (0.34s, model jev-1.13.0)

all checks passed.

$ uv run turnjudge calibrate run (summary lines)
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
