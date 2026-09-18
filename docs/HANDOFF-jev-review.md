# Handoff prompt for building jev-review

Copy everything below the line into a fresh agent context.

---

You are building **jev-review**, an end-of-turn semantic review tool for coding agents. It
snapshots the agent's delta at the end of each Claude Code turn, redacts it, asks TypeSafe's
System One model (Jev) a fixed set of typed questions about complexity, maintainability,
behavioral risk, and security, applies a policy in code, and feeds templated findings back to
the agent through a Stop hook. The full specification is in
`~/Work/jev-playgorund/docs/SPEC-jev-review.md`. Read it completely before doing anything.

## Ground rules

1. **Follow the TypeSafe skill.** It is installed as the `typesafe@typesafe-ai` plugin. Its
   file is at `~/.claude/plugins/marketplaces/typesafe-ai/skills/typesafe-ai/SKILL.md`. It says
   the live docs at `https://docs.typesafe.ai/llms.txt` are the source of truth. Read the API
   page, the Python SDK usage page, and the primitive pages for Choice, Score, and Noul before
   writing any question. Verify SDK signatures against the installed package, not the docs
   summaries; the installed `typesafe-sdk` exposes `result.scores[...]`, `result.nouls[...]`,
   `result.choices[...]`, and `result.usage` with `input_tokens`, `output_tokens`, and
   `billing_units`.
2. **Follow the Claude Code hooks reference** at `https://code.claude.com/docs/en/hooks`.
   Verify the Stop hook's `stop_hook_active` and `last_assistant_message` fields, the
   `decision`/`reason` output for Stop, `prompt` on UserPromptSubmit, and plugin `hooks/hooks.json`.
3. **The repo is private and stays private.** Create it at `~/Work/jev-review` as a new
   git repo. Do not create a GitHub remote, publish a package, publish an artifact, or make
   anything public. Will signs off on publication separately.
4. **Key handling.** The TypeSafe key is read from `TYPESAFE_API_KEY` or
   `~/.config/jev-review/key` (0600). Never commit it, never write it into settings files, never
   print it. A working key is available in `~/Work/jev-playgorund/.env` for this build;
   copy it to the key file location once and use that. The playground's `.env` will be deleted.
5. **Prior art you can reuse.** `~/Work/jev-playgorund` has two working Jev pipelines
   (`src/jev_playground/scan.py` and `src/jev_playground/email/triage.py`). The facts-plus-
   question-set-plus-decide() split, the JSONL checkpointing, the msgspec usage serialization,
   and the dry-run mode are all patterns to carry over. Do not depend on that package.
6. **Repos to calibrate on** (all local, all git): `~/Work/nests` (Go), `~/Work/agentic-sw-factory`
   (TypeScript), `~/Work/qb-harness` (Python), `~/Work/billy-blog` (Svelte). Note
   `~/Work/nests-*` directories are worktrees of nests; do not double count them.
7. **Never block on failure.** Re-read SPEC §3.10 before writing the Stop hook. A hook that
   stalls the agent when the API is down is a shipping bug, not an edge case.
8. **Report faithfully.** When you write `docs/READINESS.md`, every checkbox must point at the
   file, test, or log line that proves it. If a criterion is not met, say so and why.

## Build order

Work in the order of SPEC §8. Phase 0 comes first and gates everything: build `calibrate`,
produce `calibration/report.md` from at least 20 labeled deltas you label yourself using the
criteria text, and stop to show Will the report before writing any hook code. Label files are
YAML; Will will correct your labels, and the corrected file becomes the calibration set.

Then Phases 1 through 4. Commit at the end of each phase with a message that names the phase.
Dogfood from Phase 2 onward: enable the hooks in the repo's own `.claude/settings.json` and let
the tool review your own turns. Keep the audit log; it is a deliverable.

Do not start Phase 5 (blog draft, public repo prep). That is a separate handoff once Will has
marked the system ready.

## Definition of done for this handoff

Iterate until every item in SPEC §7 is either checked with evidence in `docs/READINESS.md` or
listed there as not met with the reason and what it would take. Criteria 2 and 4 need Will's
labels and session marks; when you reach a point where only his input can move a criterion,
finish everything else, then stop and tell him exactly what you need: which labels to correct,
which blocks to mark helpful or not, on which sessions.

## Goal statement for the iteration loop

> Make jev-review ready as defined by SPEC §7. On each iteration: run the full test suite, run
> `calibrate` against the current labeled set, run `doctor`, and diff `docs/READINESS.md`
> against the criteria. Fix the highest-value gap first: a failing test, then a security or
> redaction gap, then a calibration miss, then a dogfood complaint, then polish. Stop iterating
> when READINESS.md is complete or when the remaining gaps need Will's input, and report which.
