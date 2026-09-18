# Calibration data

- `labels.yaml`: the labeled set (91 file deltas). Real entries name a repo, commit, and file
  path in one of Will's private repositories; the notes describe the change in one sentence.
  Synthetic entries point at the bundled repo in `synthetic/`.
- `responses-synthetic/`: recorded Jev answers for the synthetic pairs, tracked and used by
  `tests/test_integration.py`.
- `responses/`, `responses-v1/`, `responses-v2/`, `responses-v3/`: recorded answers for the real
  deltas. These contain redacted diff excerpts from private repositories, so they are kept
  outside the public repo (a symlink to `~/.local/state/turnjudge/calibration-private/`) and were
  removed from git history on 2026-09-17 before the repo went public. `calibrate run` reuses them
  when present and re-asks Jev when not; anyone else running calibration against their own repos
  gets their own.
- `report.md`: generated from labels plus responses. Per-delta rows show repo, short sha, file
  path, and answers; no diff text.
- `assessment.md`: hand-written reading of each calibration run, appended to the report.
- `review-notes.md`, `labels-v1.yaml`, `labels-reviewed.yaml`: the independent re-labeling pass.
- `experiments/`: things tried and kept or reverted, with numbers.
