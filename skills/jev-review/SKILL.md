---
name: jev-review
description: Run jev-review on the current delta and show the full per-file answer table, the fired rules, and how to tune the standards. Use when the user asks what jev-review thinks of the current changes, why it blocked or advised, or how to adjust its thresholds or STANDARDS.md.
---

# /jev-review

jev-review judges the turn's delta with TypeSafe's Jev and decides in code. This skill runs the same
`check` path the Stop hook runs, in explain mode, and prints everything the policy saw.

## Run it

```
uv run --quiet --project "${CLAUDE_PLUGIN_ROOT}" jev-review explain
```

By default `explain` reviews the working tree against `HEAD` plus untracked files. To review only
the current turn's delta, set `JEV_REVIEW_SESSION` to the session id (hooks record it per session)
or pass a task description with `JEV_REVIEW_TASK="..."` so the unrequested-change question has
something to compare against. Add `--json` for machine-readable output.

Show the user the table and the fired rules verbatim. Then say, in one or two sentences per fired
rule, what in the diff most likely drove it. Do not paraphrase the numbers.

## Read the table

- Scores are positions on 0..3 (verbosity 0..2): `beh` behavior added, `cflow` control flow added,
  `abstr` abstraction added, `maint` maintenance risk, `verb` verbosity.
- Nouls are probabilities of yes: `unnec` unnecessary complexity, `swall` swallows a failure,
  `unreq` unrequested behavior change, `tests` tests proportional (high is good), and the four
  security labels `secret`, `input`, `weaken`, `extsurf`.
- The policy and every threshold live in `jev-review.toml` (defaults) and `<repo>/.jev-review.toml`
  (overrides). `src/jev_review/policy.py` is the only place answers become outcomes.

## Tune it

1. First knob: `STANDARDS.md` in the repo (`jev-review init` writes a starter). It travels with every
   request as `standards`, and the complexity and verbosity questions judge against it. Say what
   the project considers proportionate; that moves the judgments before any threshold changes.
2. Second knob: `.jev-review.toml` `[thresholds]`. Raise a `*_block` value to block less often, or
   set `mode = "advise"` to never block. Values are uncalibrated until `calibration/report.md` in
   the jev-review repo says otherwise; quote that report when suggesting a change.
3. Withheld files: the `[redact] deny_paths` list and the built-in deny list never leave the machine.
   The audit log at `~/.local/state/jev-review/<project>/audit/<date>.jsonl` is the record of what did.

## Mark a block

After a block, the user can record whether it helped:

```
uv run --quiet --project "${CLAUDE_PLUGIN_ROOT}" jev-review feedback x list
uv run --quiet --project "${CLAUDE_PLUGIN_ROOT}" jev-review feedback <session-prefix>/<turn> helpful --note "..."
```
