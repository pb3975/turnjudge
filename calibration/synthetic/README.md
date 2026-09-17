# Synthetic complexity pairs

Built 2026-09-17 by an agent at Will's direction, because 57 real deltas contained no example of
disproportionate complexity and the question could not be calibrated without positives.

`turnjudge-synthetic.bundle` is a git bundle of the throwaway repo (`git clone
turnjudge-synthetic.bundle ~/Work/turnjudge-synthetic` restores it at the path the labels use).
It holds a small codebase in Python, Go, and TypeScript, and 27 scenario branches from the same
base:

- `simple/1..12`: the proportionate change for a one-sentence task (inline, a few lines).
- `overbuilt/1..12`: the same task done the way an eager agent might, with a strategy interface for
  one case, a registry with one entry, config-driven dispatch for one value, a builder, or a
  generic base class. Correct, plausible, 57 to 131 added lines.
- `requested/13..15`: tasks that explicitly ask for structure; the diff builds it.

Every checkout passes its language's tests and type checks. Labels are in
`../labels-synthetic.yaml` and were merged into `../labels.yaml`. The four `index.ts` re-export
entries the agent flagged were dropped. Recorded answers are in `../responses-synthetic/` and
copied into `../responses/`.

## Result

`unnecessary_complexity` separates the set completely: all 19 over-built files scored 0.50 to
0.87, all 15 simple and requested files scored 0.06 to 0.45. The three requested-structure files
scored 0.12, 0.18, and 0.23 despite abstraction ratings of 2 to 3, which is the distinction the
question exists to make. On the 57 real deltas no clean file exceeds 0.36.

The shipped block rule never fired on any of them because it required `behavior_added` at or
under 1.0, and an over-built change still delivers the requested behavior (the model rated it 1.1
to 2.5). The rule was changed on 2026-09-17: block at 0.70 when abstraction or control flow is at
level 2 or more, advise at 0.50 with no gate. On the synthetic set that blocks 13 of 19 and
advises the other 6 with zero false positives; on the real set it fires on nothing clean.
