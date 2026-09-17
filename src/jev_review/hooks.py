"""Hook entry points. Filled in during Phase 2; Phase 0 only needs the CLI to import."""

from __future__ import annotations

from pathlib import Path


def run_hook(cmd: str, *, explain: bool = False, event_override: str | None = None, config_path: str | None = None) -> int:
    return 0


def run_explain(*, config_path: str | None = None, as_json: bool = False) -> int:
    return 0


def run_doctor(*, quiet: bool = False, config_path: str | None = None) -> int:
    return 0


def run_init(path: Path, *, force: bool = False) -> int:
    return 0


def run_feedback(session_prefix: str, mark: str, note: str, *, config_path: str | None = None) -> int:
    return 0
