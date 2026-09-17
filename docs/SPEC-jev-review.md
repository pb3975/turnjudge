# jev-review: end-of-turn semantic review for coding agents

**Status:** specification v1, 2026-09-16. Project name is a placeholder; rename freely.
**Owner:** Will Metz. **Builder:** a fresh agent context, see `HANDOFF-jev-review.md`.

## 1. Purpose

Coding agents already run linters, type checkers, and tests. Those answer "what measurable
properties does this code have?" They do not answer "does this change add complexity the task
did not ask for?", "does this swallow a failure that used to surface?", or "did this weaken a
security check?". jev-review asks those questions of the agent's delta at the end of every
turn, using TypeSafe's System One model (Jev), and hands the agent typed, templated feedback it
must address before the turn is allowed to end.

Jev returns probabilities and typed answers, never prose. All feedback text is authored in this
repo. That closes the prompt-injection channel a text-generating reviewer would open: nothing the
evaluator says can carry instructions, because the evaluator only says numbers.

## 2. Principles

1. **Jev judges; code decides.** Every question is one narrow semantic judgment. Keep/block
   policy, thresholds, and weights live in code and config, and re-running policy costs nothing.
2. **Intent is part of the state.** "Disproportionate" only means something relative to what
   was asked. The user's prompt for the turn travels with the diff.
3. **Never block on infrastructure failure.** If the API is down, slow, or the key is missing,
   the hook exits 0 with a one-line notice. A review tool that stalls the agent gets uninstalled.
4. **Block at most once per turn.** A second Stop in the same turn is always allowed through.
5. **Nothing leaves the machine unredacted, uncapped, or unlogged.**
6. **Calibrate before enforcing.** No threshold ships without a labeled set that justifies it.

## 3. Architecture

```
UserPromptSubmit hook ──► jev-review mark   (snapshot tree, save prompt)
                                          │
Stop hook ────────────► jev-review check   (delta → redact → Jev → policy → feedback)
                                          │
                              ┌───────────┴───────────┐
                              │ exit 0 + systemMessage │  nothing to say / advisory only
                              │ JSON decision=block    │  reason = templated feedback
                              └───────────────────────┘
/jev-review skill ────► jev-review check --explain   (on demand, same code path)
jev-review calibrate ─► historical commits + labels → agreement report + threshold suggestions
```

### 3.1 Packages and layout

Python 3.12+, `uv`, `typesafe-sdk`. Single package `jev_review` with one CLI entry point.
Ship as a Claude Code plugin so the hooks and skill install together and are shareable.

```
jev-review/
  pyproject.toml
  src/jev_review/
    cli.py           # mark | check | calibrate | explain | doctor
    delta.py         # turn snapshot and per-file diff extraction
    redact.py        # secret scrubbing, deny lists, size caps
    questions.py     # the question set (single source of truth)
    state.py         # builds the System One state object
    policy.py        # thresholds, severities, feedback templates
    client.py        # TypeSafe client wrapper: retries, timeout, fixture recording
    hooks.py         # stdin JSON parsing and hook JSON output
    store.py         # per-project state dir, audit log, calibration data
  .claude-plugin/plugin.json
  hooks/hooks.json
  skills/jev-review/SKILL.md
  STANDARDS.md                 # default standards block, copied into projects on init
  jev-review.toml              # default config
  tests/
  calibration/                 # labeled deltas and recorded Jev responses
  docs/
```

### 3.2 Delta extraction (`delta.py`)

The unit of review is **the turn's delta**, not the diff against HEAD. Agents often work
across many turns before committing, and each turn should be judged on what it did.

- `mark` (UserPromptSubmit): build a tree object from the working tree without touching the
  real index: `GIT_INDEX_FILE=<tmp> git add -A && git write-tree`. Record the tree SHA, the
  prompt text, and a timestamp in the project state dir. Respect `.gitignore`.
- `check` (Stop): build the end tree the same way, then `git diff <start> <end>` with
  `--unified=10 --function-context` where the language supports it, split per file.
- If no `mark` exists for this session, fall back to `git diff HEAD` plus untracked files and
  say so in the audit log.
- Skip binary files, files over the size cap, generated files, lockfiles, and anything matching
  the deny list. Pure deletions and pure renames are reported but not judged.
- A delta over N files (default 12) or M total bytes (default 60 KB after redaction) is
  reviewed in advisory mode only, never blocking, with a notice that the delta was too large to
  judge reliably.

### 3.3 Redaction and limits (`redact.py`)

Runs on every diff before anything is sent. Tests must cover each rule.

- **Deny list** (never sent, file is reported as "withheld"): `.env*`, `*.pem`, `*.key`,
  `id_*`, `*.p12`, `*secrets*`, `*credentials*`, lockfiles, `*.min.*`, and anything under
  paths listed in `jev-review.toml [redact] deny_paths`.
- **Secret patterns** (replaced with `<REDACTED:kind>`): AWS access keys, private key blocks,
  JWTs, GitHub/GitLab/Slack/Stripe token prefixes, `apikey_` and `sk-` style prefixes,
  `Authorization: Bearer ...`, URLs with userinfo, and any string over 32 chars with entropy
  above a threshold that sits in an assignment or header context.
- **Identity trimming**: home directory paths are rewritten to `~`, and the user's email and
  machine hostname are replaced with placeholders.
- **Caps**: per-file diff ≤ 12 KB after redaction, total ≤ 60 KB, prompt text ≤ 2 KB.
- **Audit**: every request's state is appended, post-redaction, to
  `<state_dir>/audit/<date>.jsonl` with session id, tree SHAs, token usage, and answers.
  This file is what the user reviews to confirm what left the machine.

### 3.4 State (`state.py`)

One request per changed file. Object, not string, so each part is named.

```json
{
  "task": "<the user's prompt for this turn, truncated>",
  "standards": "<contents of STANDARDS.md for this project>",
  "repo": {"name": "nests", "language": "go"},
  "file": {"path": "internal/session/turn.go", "lines_added": 41, "lines_removed": 3},
  "diff": "<redacted unified diff with function context>",
  "turn_summary": "<last_assistant_message, truncated to 1 KB>"
}
```

`turn_summary` lets the "behavior the task did not ask for" question see what the agent claims
it did. `standards` is short, plain English, and project-specific; it is the equivalent of the
email triage policy file and is the primary knob a user turns before touching thresholds.

### 3.5 Question set (`questions.py`)

All questions are asked together in one request per file. IDs are for code; instructions carry
full meaning. Criteria below are the v1 wording and are expected to change during calibration.

**Complexity**

- `behavior_added` (Score, 4 levels): none / small fix or tweak / one new observable capability
  or code path / several capabilities or a substantial feature.
- `control_flow_added` (Score, 4 levels): no new branches, loops, or early returns / one or two
  simple conditions or a loop / nested conditions, multiple loops, or new error paths / deeply
  nested logic, state machines, or many interacting branches.
- `abstraction_added` (Score, 4 levels): none, changes are inline / one helper or type used
  right here / a new interface, base class, generic, or indirection layer / a framework-like
  layer: registries, plugins, factories, config-driven dispatch.
- `unnecessary_complexity` (Noul): the control-flow or abstraction complexity this diff adds
  is disproportionate to the behavior it adds, given `task` and `standards`.

**Maintainability**

- `maintenance_risk` (Score, 4 levels): localized and straightforward / adds some interaction
  or indirection but behavior stays clear / adds coupled branches or responsibilities that need
  substantial context to modify safely / makes behavior hard to reason about or creates
  significant change risk.
- `verbosity` (Score, 3 levels): nothing beyond what the task needs / some boilerplate,
  comments restating code, or redundant checks / substantial padding, over-defensive checks,
  or duplicated logic.

**Behavioral risk**

- `swallows_failure` (Noul): hides or swallows a failure that previously surfaced, for example
  a broad except that returns a default, a logged-and-ignored error, or a removed assertion.
- `unrequested_behavior_change` (Noul): changes behavior that `task` did not ask for and
  `turn_summary` does not disclose.
- `tests_proportional` (Noul): the change includes tests proportional to the behavior added,
  or the task explicitly did not call for tests.

**Security** (one Noul per label because several may apply)

- `introduces_secret`: adds a hardcoded credential, token, key, or password.
- `unsafe_input_use`: passes untrusted input to a shell, `eval`, SQL, a filesystem path, or a
  deserializer without validation.
- `weakens_check`: removes or loosens validation, authentication, authorization, TLS
  verification, or a safety check.
- `new_external_surface`: adds a new network call, dependency, or executable download.

Each Noul carries `true` and `false` criteria naming concrete situations.

### 3.6 Policy (`policy.py`, `jev-review.toml`)

Policy maps answers to one of three outcomes per file, then the worst outcome wins for the turn:

| Outcome | Effect on the agent |
|---|---|
| `pass` | Nothing. Optionally a one-line `systemMessage` summary. |
| `advise` | Turn ends. Feedback is delivered as `systemMessage` for the next turn. |
| `block` | `decision: block` with `reason` = templated feedback. Agent must respond. |

Default rules, all thresholds in config and all marked "uncalibrated" until §7 passes:

- Any security Noul ≥ 0.85 → block.
- `swallows_failure` ≥ 0.85 → block.
- `unrequested_behavior_change` ≥ 0.80 → block.
- `unnecessary_complexity` ≥ 0.80 and (`control_flow_added` ≥ 2.0 or `abstraction_added` ≥
  2.0) and `behavior_added` ≤ 1.0 → block.
- `maintenance_risk` ≥ 2.2 with confidence ≥ 0.6 → advise.
- `verbosity` ≥ 1.5 → advise.
- `tests_proportional` ≤ 0.3 and `behavior_added` ≥ 2.0 → advise.
- Composite dashboard score is computed for logging only; it never drives a decision.

Feedback templates are fixed strings with slots for file path, the fired rule, and the two
Score levels that matter, e.g.:

> jev-review: `internal/session/turn.go` adds a new indirection layer (abstraction 2.6/3) for a
> change judged as a small fix (behavior 0.8/3). Task: "fix the nil deref in resume". Either
> simplify to an inline change or explain in your reply why the abstraction is needed.

The agent may push back. The block fires once; the second Stop passes. The user sees the
feedback in the transcript and makes the call.

### 3.7 Hook integration (`hooks.py`, `hooks/hooks.json`)

- **UserPromptSubmit** → `jev-review mark`. Reads `prompt`, `session_id`, `cwd`. Exit 0 always.
  Timeout 10 s.
- **Stop** → `jev-review check`. Reads `session_id`, `cwd`, `stop_hook_active`,
  `last_assistant_message`. If `stop_hook_active` is true or the session's state file shows a
  block already issued this turn, exit 0 immediately. Timeout 60 s; on timeout exit 0.
- **SubagentStop** → same as Stop, advisory only by default (config switch).
- **SessionStart** → `jev-review doctor --quiet`: verifies key, git, and config; prints one
  line via `systemMessage` if something is off. Never blocks.
- Output uses the documented JSON schema: `{"decision":"block","reason":"..."}` for blocks,
  `{"systemMessage":"..."}` for advisories, empty stdout and exit 0 for pass.
- The hook command is `uv run --project ${CLAUDE_PLUGIN_ROOT} jev-review <cmd>` in exec form
  with `args`, so no shell interpolation of untrusted input.

### 3.8 Skill (`skills/jev-review/SKILL.md`)

`/jev-review` runs `check --explain` on the current delta and prints the full per-file answer
table with probabilities, plus the fired rules. It also explains the standards and how to tune
them. It calls the same CLI; there is no second implementation.

### 3.9 Key handling and security requirements

- The API key is read from `TYPESAFE_API_KEY` or from `~/.config/jev-review/key` (mode 0600).
  It is never read from a project directory, never written to settings.json, and never logged.
- `doctor` refuses to run if the key file is group- or world-readable.
- Only the redacted state object is sent. The repo is never uploaded. The audit log is the
  contract for what left the machine.
- Hook scripts run with the user's privileges and do not need network access beyond
  `api.typesafe.ai`. Document this so users can firewall it.
- No telemetry. No third-party calls other than TypeSafe.
- The tool's own repo runs jev-review on itself (dogfooding is an acceptance criterion).

### 3.10 Failure handling

| Condition | Behavior |
|---|---|
| No git repo, or no changes | exit 0, nothing printed |
| Key missing or invalid | exit 0, `systemMessage` once per session: "jev-review disabled: no key" |
| API 429/529 after SDK retries, or timeout | exit 0, `systemMessage`: "jev-review skipped: service unavailable" |
| Delta over caps | advisory only, with notice |
| Redaction withheld every file | exit 0, notice listing withheld paths |
| Any unhandled exception | exit 0, error written to state dir, never to the agent |

## 4. Calibration and the baseline lab (`jev-review calibrate`)

This is the first thing built, before hooks, because it decides whether the project is worth
finishing.

- Input: a repo path, a commit range, and a labels file `calibration/labels.yaml` where each
  entry is `{repo, sha, file, labels: {unnecessary_complexity: yes|no, maintenance_risk: 0-3,
  swallows_failure: yes|no, ...}, note}`. Labels are the user's judgment.
- The command reconstructs each file delta at that commit, builds the same state (with the
  commit message standing in for `task`), asks the same questions, records raw answers to
  `calibration/responses/<sha>-<file>.json`, and reports per question: agreement with labels,
  Brier score for Nouls, mean absolute error for Scores, and the threshold that maximizes
  agreement on this set.
- Unlabeled runs over a repo's history produce the **baseline**: per-repo distributions of every
  answer, so a new delta can be reported as a percentile within its own repo. The Stop hook
  includes the percentile in feedback when a baseline exists.
- Recorded responses double as test fixtures. Policy and template tests run against them
  offline.

## 5. Configuration (`jev-review.toml`)

```toml
[review]
mode = "block"            # block | advise | off
subagents = "advise"
max_files = 12
max_total_bytes = 60000
per_file_bytes = 12000
timeout_seconds = 45
model = "jev-latest"

[thresholds]              # every value here is uncalibrated until calibration/report.md says otherwise
security_block = 0.85
swallows_failure_block = 0.85
unrequested_change_block = 0.80
unnecessary_complexity_block = 0.80
maintenance_advise = 2.2
verbosity_advise = 1.5

[redact]
deny_paths = ["infra/secrets/**"]
extra_patterns = []

[paths]
standards = "STANDARDS.md"
state_dir = "~/.local/state/jev-review"
```

Project-level overrides live in `<repo>/.jev-review.toml`. `jev-review init` writes that file
and a starter `STANDARDS.md` into a project.

## 6. Testing

- **Unit**: redaction (one test per pattern, plus a corpus of 50 known-secret strings and 50
  false-positive candidates), delta extraction (untracked, renamed, deleted, binary, over-cap),
  policy (every rule fires and does not fire at its boundary), templates (every slot fills).
- **Hook contract**: feed documented stdin JSON for each event, assert exact stdout and exit
  code, including `stop_hook_active=true`, missing mark, no git, and exception paths.
- **Loop safety**: simulate three consecutive Stops in one turn; assert exactly one block.
- **Offline integration**: the full `check` path against recorded Jev responses.
- **Live smoke**: one real request per question type, skipped without a key.
- **Calibration gate**: see §7.
- **Latency**: `check` on a 6-file delta completes in under 8 s wall time with 6 requests in
  flight, measured and recorded in `calibration/report.md`.
- **Dogfood**: the repo's own `.claude/settings.json` enables the hooks; the builder's own turns
  are reviewed, and the audit log from that is part of the deliverable.

## 7. Definition of Ready

The system is ready when all of the following are true and recorded in `docs/READINESS.md`:

1. All tests in §6 pass in CI and locally.
2. `calibration/labels.yaml` has at least 40 labeled file deltas from at least three repos,
   half of which the user considers clean and half of which the user would have pushed back on.
3. On that set, `unnecessary_complexity` and `swallows_failure` reach ≥ 0.80 agreement at
   their shipped thresholds, and each security Noul has no false positive above its threshold.
   Scores have MAE ≤ 0.6 levels.
4. Ten real agent sessions on at least two of the user's repos ran with the hooks enabled. The
   audit log shows every block, the user marked each block as helpful or not, and at least 7 of
   10 blocks were marked helpful with no session stalled.
5. `doctor` passes on a fresh machine following only the README.
6. The redaction corpus has zero leaks, and the audit log for the dogfood sessions was reviewed
   by the user and contains nothing they would not paste in public.
7. The plugin installs from the repo via `claude plugin marketplace add` and
   `claude plugin install`, and `/jev-review` works.

## 8. Phases

0. **Calibration lab** (first): `calibrate` command, labels from nests, agentic-sw-factory, and
   qb-harness, first report. Decide whether to continue based on the report.
1. **CLI**: delta, redaction, state, questions, policy, audit, `check --explain`.
2. **Hooks**: mark and check, loop guard, failure handling, settings snippet.
3. **Plugin and skill**: packaging, `init`, `doctor`, README.
4. **Dogfood**: ten sessions, feedback marks, threshold tuning, READINESS.md.
5. **Publication prep**: the repo stays private. Draft a Forty First Hour post in `build-log`
   format with `draft: true`, following the vault's Publish-Ready Checklist. Screenshots come
   from scripted, redacted sessions. Nothing goes public until Will signs off on the staged
   preview and separately on making the repo public.

## 9. Non-goals

- Replacing linters, type checkers, tests, or human review.
- Judging whole repositories or whole PRs in v1. The unit is the turn's delta per file.
- Generating fix suggestions in prose. Feedback names the problem; the agent fixes it.
- Supporting non-git projects.
- Any hosted component.

## 10. Open questions for calibration to answer

- Is per-file the right unit, or do some judgments (unrequested behavior change) need the whole
  turn delta as one state? Try both on the labeled set.
- Does `--function-context` improve agreement enough to justify the tokens?
- Is a 4-level Score better than 3 for control flow and abstraction on real deltas?
- Should the Stop hook run only when the agent's turn touched code, or also on doc-only turns
  with a reduced question set?
