"""Builds the System One state object for one file delta. Object, not string, so each part is named."""

from __future__ import annotations

from dataclasses import dataclass

from jev_review.config import Config
from jev_review.delta import FileDelta
from jev_review.redact import Redacted, redact_diff, redact_text


@dataclass
class FileState:
    path: str
    state: dict | None          # None when withheld
    redacted: Redacted
    lines_added: int
    lines_removed: int


def build_state(*, task: str, standards: str, repo_name: str, language: str, delta: FileDelta,
                turn_summary: str, cfg: Config, emails: list[str] | None = None,
                turn_files: list[dict] | None = None) -> FileState:
    red = redact_diff(delta.path, delta.diff, per_file_bytes=cfg.per_file_bytes,
                      extra_deny_paths=cfg.deny_paths, extra_patterns=cfg.extra_patterns, emails=emails)
    if red.withheld_reason:
        return FileState(delta.path, None, red, delta.lines_added, delta.lines_removed)
    state = {
        "task": redact_text(task or "(no task recorded)", cfg.prompt_bytes, "task", emails),
        "standards": standards,
        "repo": {"name": repo_name, "language": language},
        "file": {"path": delta.path, "language": delta.language, "status": delta.status,
                 "lines_added": delta.lines_added, "lines_removed": delta.lines_removed},
        "diff": red.text,
        "turn_summary": redact_text(turn_summary or "(no summary)", cfg.summary_bytes, "turn_summary", emails),
        "turn_files_changed": turn_files or [{"path": delta.path, "status": delta.status,
                                              "lines_added": delta.lines_added, "lines_removed": delta.lines_removed}],
    }
    return FileState(delta.path, state, red, delta.lines_added, delta.lines_removed)
