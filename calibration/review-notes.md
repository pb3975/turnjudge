# Independent review of the calibration labels

Produced by an independent reviewer agent on 2026-09-17. Every entry in `labels.yaml` was
re-judged blind from the diff, the commit message and the criteria text in
`src/turnjudge/questions.py`, then compared with the existing labels. The 12 `turnjudge/dogfood`
agent commits were labeled afresh. Output: `labels-reviewed.yaml`.

## Counts

| set | entries | clean | pushback |
|---|---|---|---|
| Part 1 (re-labeled existing) | 38 | 25 | 13 |
| Part 2 (dogfood agent commits) | 19 | 14 | 5 |
| **total** | **57** | **39** | **18** |

## Verdict changes (Part 1)

| repo | sha | file | old | new | why |
|---|---|---|---|---|---|
| ~/Work/nests | b7fc6012cc | internal/reconcile/reconcile.go | clean | pushback | A reorder of host-loss cleanup into two passes with new budget arithmetic that decides whether a Nest stays assigned to a dead host. The reconciler has a test suite and this commit touches none of it. Labels were already `maintenance_risk: 2` and `tests_proportional: no`; a careful reviewer would ask for a test of the retry path, which is the pushback criterion. |
| ~/Work/agentic-sw-factory | 1d7cf9a2fc | apps/server/src/factory/refresh.ts | clean | pushback | `findReadyIssue` maps every `readDirectory` and `readFileString` failure to an empty value via `orElseSucceed`. An unreadable issue file makes the scheduled lane exit 0 having done nothing and nothing reports it. This is the same fail-open shape that earned `paused.ts` (c083057) a pushback in the original set; the original note itself called it "worth a look". Labeled `swallows_failure: yes` for consistency with the criteria text. |
| ~/Work/qb-harness | 57a64d12ec | src/agentlab/cli.py | clean | pushback | Besides adding `--provider` and `--base-url`, the diff changes the default provider to `ollama` and the default model from `gpt-5.4-mini` to `qwen3:8b`. The message ("Add local Ollama provider support") says add, not switch. A reviewer would ask whether the default flip was intended. |

All 12 pushback verdicts in the original set were confirmed. No pushback was downgraded to clean.

## Label disagreements of more than one level or a flipped yes/no (Part 1)

No score differed by more than one level. Six scores differed by exactly one level
(72977cb382 verbosity 1→0, 1a8127230e agent.go behavior 1→2, 082e90b68e agent.go abstraction 2→1,
4d3f9af31b analytics.ts abstraction 1→0 and maintenance_risk 2→1, 020cedffed control_flow 1→2);
these are within normal calibration noise and are not tabled.

| repo | sha | file | label | old | new | why |
|---|---|---|---|---|---|---|
| ~/Work/agentic-sw-factory | 1d7cf9a2fc | apps/server/src/factory/refresh.ts | swallows_failure | no | yes | New code where an I/O error on an existing file is replaced by an empty value and the caller cannot tell; the criteria list exactly this. The original note argued "new code, so nothing previously surfacing is hidden", but the criteria text explicitly includes new code. |
| ~/Work/agentic-sw-factory | 4d3f9af31b | apps/web/src/components/learning-state-sync.tsx | tests_proportional | no | yes | `apps/web/e2e/public-course.spec.ts` in the same commit has "another tab reflects progress and reset" and "storage denial still permits learning" tests, which exercise exactly the cross-tab storage listener and the warning this component renders. |
| ~/Work/qb-harness | 57a64d12ec | src/agentlab/tools.py | tests_proportional | no | yes | The one changed line in `tests/test_tools.py` calls `write_file` with the new `lines` list and asserts the file reads back as `alpha\nbeta\n`, which is the new join-plus-trailing-newline behavior. That is a test that exercises the change. The verdict stays pushback on the undisclosed contract change. |
| ~/Work/qb-harness | 57a64d12ec | src/agentlab/cli.py | unrequested_behavior_change | no | yes | The default provider and default model change; the message does not mention either. |

## Part 2 findings worth relaying

- **n2 (d5e32a49b1, nests `internal/cli/agent.go`) — pushback.** The fix matches `errors.Is(err, context.DeadlineExceeded)`, but the real probe path is `ExecInVM` → `exec.CommandContext` → `cmd.Run()`. When the context expires Go kills the process and `Run` returns an `*exec.ExitError` (the process error is preferred over the context error), which `ExecInVM` turns into exit code -1 with a nil error; `probeSession` then returns an "inspecting session … failed (exit -1)" error. So a real timeout still fails the command. The test passes only because the fake harness returns `context.DeadlineExceeded` directly. Checking `probeCtx.Err() != nil` after the call would work. The new 10 s deadline on every `status` call is also behavior the task did not ask for.
- **b1 (673c05e242, billy-blog `src/lib/server/ingest.ts`) — pushback.** `unreadable()` returns true on any `accessSync` error, including ENOENT. chokidar 5.0.0 (the pinned version) checks `!this._isIgnored(path)` before emitting `unlink`, so a deleted photo no longer produces the event that triggers the rescan marking it missing. That is an undisclosed regression in addition to the silent (unlogged) skip.
- **b3 (53709cfd60, billy-blog `src/lib/server/thumbs.ts`) — pushback.** `catchAll` covers every sharp or write failure, not just HEIC, and the placeholder is renamed into the cache as the permanent thumbnail.
- **n3 (707d7be971, nests `internal/config/config.go`) — pushback.** The recognized-key sets are hand-maintained maps mirroring the struct yaml tags; a new field yields a false "unknown key" warning until someone updates the map. The five CLI files in the same commit are plumbing and labeled clean, with a note that the warn loop is pasted four times.
- **a2 (3c72b707ab, agentic-sw-factory `apps/server/src/audit/audit.ts`) — pushback.** Correct in substance, but `fetchAndRead` takes a `source` parameter it never reads, and a `pageToText` failure is recorded with `reason: "network"`.
- Everything else in Part 2 (n1, a1, a3, q1 rerun, q2, q3, b2) is clean and proportionally tested.

## Skipped

| repo | sha | reason |
|---|---|---|
| ~/Work/qb-harness | d27a2271d2 (`turnjudge dogfood q1`) | Empty commit: `git show --stat` lists no files. The rerun 4abf337094 carries the change and is labeled. |
| ~/Work/qb-harness | 66776bc5fd `.gitignore` | Not a code file (one ignore line). Mentioned in the `agent.py` note. |
| ~/Work/nests | 707d7be971 `internal/cli/cli_test.go`, `internal/config/config_test.go`; and every other `*_test.*` file in Part 2 | Pure test files skipped because each commit has a non-test file, per the instructions. |

## Observations on the criteria text

1. **`new_external_surface` does not cover inbound surface.** The name suggests a new endpoint or route counts, but the true criterion lists only outgoing HTTP/socket calls, new dependencies, and executable downloads. b2's `GET /api/health` is a new unauthenticated route and gets `no`. Either rename the label or add "exposes a new route, port, or listener" to the true criterion.
2. **`swallows_failure` vs a requested fallback.** b3 asks for a placeholder instead of a throw; the criteria give no way to distinguish "requested, narrowly scoped recovery" from "catch-all that hides unrelated failures". I labeled on breadth (catch-all → yes), but the model will see the task asked for a fallback and may say no. The instruction sentence could add "even when the task asked for a fallback, if the recovery is broader than the failure named".
3. **`swallows_failure` for new code that fails open.** The original labeler read it as "removed error handling only" for refresh.ts but "fail-open" for paused.ts. The criteria text already includes new code; the instruction sentence ("hides, swallows, or defaults away a failure") could say "including new code" up front so both readings converge.
4. **`tests_proportional` when the project has no test suite.** billy-blog 34ad5203db gets `no` three times by the letter of the criterion even though no test was possible. Either add "or the project has no test suite" to the true criterion or accept that this label is noise for such repos.
5. **`tests_proportional` for non-code artefacts** (deploy.sh, smoke.sh, .gitignore): "this file is itself a test" covers smoke.sh, but a deploy script gets `yes` only by a generous reading of "adds no behavior". Worth a clause for scripts and config.
6. **`control_flow_added` level 2 says "multiple loops"**: two trivial 2-line loops (n3 commands.go) literally qualify, which over-scores plumbing. "Multiple *interacting* loops" or "loops with non-trivial bodies" would fit intent better.
7. **`unrequested_behavior_change` and bugs.** 082e90b68e harness.go makes high-autonomy sessions unstoppable, and b1 suppresses unlink events. Both are unintended side effects rather than deliberate scope creep. I labeled b1 `yes` (the diff does change a flow outside scope) and harness.go `no` (the intended change is in scope and the bug is in the same flow). The criteria do not say whether an unintended regression counts; a sentence either way would remove that ambiguity.
8. **`abstraction_added` level 1 vs 2 for a small struct with an interface method.** 082e90b68e agent.go adds `desiredIntent` (a local struct) and a method on the `AgentIntentStore` interface. The original labeled 2, I labeled 1. The level text ("a new interface … between callers and the work") reads as a whole new indirection layer; adding one method to an existing interface is not that. A clarifying phrase would help.
9. **The dogfood q1 rerun subject is the task.** "shell tool output cap" is much terser than the original q1 subject; if the rerun was judged against the original task text the labels should say so. I judged against the rerun subject as instructed.
