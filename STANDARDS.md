# Standards for changes in this project

These are the standards a change is judged against. Keep them short and plain; they are the
first knob to turn when the review is too strict or too loose, before touching thresholds.

- A change should do what the task asked and no more. Extra features, refactors, or renames
  that the task did not ask for are unrequested, even when they are improvements.
- Prefer the inline change. Add a helper, type, or interface only when it is used in more
  than one place or the task asked for it.
- Never turn a failure into silence. A failure that used to raise, exit non-zero, or assert
  should still surface; catching it to log and continue needs a stated reason.
- New behavior comes with tests unless the task said otherwise or the project has no test
  suite for that layer.
- No hardcoded credentials, tokens, or keys. Read them from the environment or a key file.
- Untrusted input never reaches a shell, an SQL string, a file path, eval, or a deserializer
  without validation.
- Do not remove or loosen validation, authentication, authorization, TLS verification, or a
  safety check without saying why.
- Comments explain why, not what. Do not restate the code.
