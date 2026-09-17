# jev-review

End-of-turn semantic review for coding agents. At the end of every Claude Code turn it snapshots
the agent's delta, redacts it, asks TypeSafe's System One model (Jev) a fixed set of typed
questions about complexity, maintainability, behavioral risk, and security, applies a policy in
code, and feeds templated findings back to the agent through a Stop hook.

Jev judges; code decides. The model only returns numbers, so nothing it says can carry
instructions. Every feedback string is authored in this repository.

Status: private, under construction. See `docs/SPEC-jev-review.md` and `docs/READINESS.md`.
