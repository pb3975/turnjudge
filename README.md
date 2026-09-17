# jev-review

End-of-turn semantic review for coding agents. At the end of every Claude Code turn it snapshots
the agent's delta, redacts it, asks TypeSafe's System One model (Jev) a fixed set of typed
questions about complexity, maintainability, behavioral risk, and security, applies a policy in
code, and feeds templated findings back to the agent through a Stop hook.

Jev judges; code decides. The model only returns numbers, so nothing it says can carry
instructions. Every feedback string is authored in this repository (`src/jev_review/policy.py`).

Status: private. See `docs/SPEC-jev-review.md` for the design and `docs/READINESS.md` for what is
and is not proven yet.

## Install

Requirements: Python 3.12+, [`uv`](https://docs.astral.sh/uv/), git, and a TypeSafe API key.

1. Put the key where the tool reads it. It is read from `TYPESAFE_API_KEY` or from
   `~/.config/jev-review/key`, which must be mode 0600. It is never read from a project directory,
   never written to a settings file, and never logged.

   ```sh
   mkdir -p ~/.config/jev-review && (umask 077; printf '%s' "$KEY" > ~/.config/jev-review/key)
   ```

2. Install the plugin from this repo (it is its own marketplace):

   ```sh
   claude plugin marketplace add /path/to/jev-review
   claude plugin install jev-review@jev-review-local          # user scope: every project
   claude plugin install jev-review@jev-review-local --scope project   # or one project
   ```

   The hooks run `uv run --project <plugin root> jev-review ...`; the first run creates the
   plugin's virtualenv, later runs start in about 0.1 s.

3. Check the setup:

   ```sh
   uv run --project /path/to/jev-review jev-review doctor
   ```

   `doctor` verifies the key and its file mode, git, the state directory, the config, and makes one
   live request. It refuses a key file that is group- or world-readable.

4. Optional, per project: `jev-review init` writes `.jev-review.toml` and a starter `STANDARDS.md`.
   The standards file is the first knob to turn; thresholds are the second.

## What happens on each turn

| Hook | Command | Effect |
|---|---|---|
| `SessionStart` | `doctor --quiet` | One-line `systemMessage` if the key, git, or config is off. Never blocks. |
| `UserPromptSubmit` | `mark` | Snapshots the working tree (a git tree object written with a temporary index) and saves the prompt. |
| `Stop` | `check` | Diffs the tree now against the mark, redacts, asks Jev per file, applies policy. `pass` prints nothing; `advise` returns a `systemMessage`; `block` returns `decision: block` with templated feedback. |
| `SubagentStop` | `check` | Same, advisory only by default (`subagents` in config). |

A block fires at most once per turn: the second Stop in the same turn always passes. If the API is
down, slow, or the key is missing, the hook exits 0 with a one-line notice. If the tool itself
fails, the error goes to `~/.local/state/jev-review/<project>/errors.log`, never to the agent.

`/jev-review` in a session runs the same `check` path in explain mode and prints the per-file answer
table and fired rules. To review a PR or any commit range instead of the working tree:

```sh
git fetch origin pull/8/head:pr8
jev-review explain --range "$(git merge-base main pr8)..pr8"
```

The commit subjects and bodies in the range stand in for the task.

## What leaves the machine

Only the redacted state object for each changed file: the task prompt (capped at 2 KB), the
project's `STANDARDS.md`, the repo name and language, the file path and line counts, the unified
diff with function context (capped at 12 KB per file, 60 KB per turn), the agent's final message
(capped at 1 KB), and the list of files the turn touched. The repo is never uploaded.

Before sending, `src/jev_review/redact.py` withholds files on the deny list (`.env*`, keys,
certificates, lockfiles, minified and generated files, anything under `[redact] deny_paths`),
replaces secret-shaped strings with `<REDACTED:kind>`, rewrites the home directory to `~`, and
replaces the git user email and hostname with placeholders. Withheld files are named in the
feedback, never sent.

The audit log at `~/.local/state/jev-review/<project>/audit/<date>.jsonl` records every request's
state exactly as sent, the answers, token usage, and the outcome. It is the contract for what left
the machine; review it.

The only network destination is `api.typesafe.ai` over HTTPS. Hooks run with your privileges and
need nothing else, so you can firewall them to that host. There is no telemetry.

## Configuration

Defaults live in `jev-review.toml` at the plugin root. A project overrides them in
`<repo>/.jev-review.toml`. Modes: `block` (default), `advise` (findings are delivered but never
block), `off`. Every threshold is marked uncalibrated until `calibration/report.md` justifies it.

## Calibration

`calibration/labels.yaml` holds labeled file deltas from real commits. `jev-review calibrate run`
reconstructs each delta, asks the same questions, records the raw answers under
`calibration/responses/`, and writes `calibration/report.md` with agreement, Brier scores, MAE,
best thresholds, and latency. Recorded responses are reused unless `--refresh` is given and
double as offline test fixtures. `calibrate candidates` lists judgeable deltas in a range;
`calibrate baseline` records per-repo answer distributions so feedback can cite a percentile.

## Feedback on blocks

```sh
jev-review feedback x list                        # every block in the audit log
jev-review feedback <session-prefix>/<turn> helpful --note "caught a real swallow"
jev-review feedback <session-prefix>/<turn> unhelpful --note "the change was asked for"
```

Marks go to `~/.local/state/jev-review/<project>/feedback.jsonl` and feed the readiness report.

## Development

```sh
uv sync
uv run pytest                      # offline; live smoke needs JEV_REVIEW_LIVE=1 and a key
uv run jev-review doctor
```

This repo runs jev-review on itself through `.claude/settings.json`.
