"""Configuration: shipped defaults in jev-review.toml, overridden by <repo>/.jev-review.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "jev-review.toml"
DEFAULT_STANDARDS_PATH = PACKAGE_ROOT / "STANDARDS.md"
PROJECT_CONFIG_NAME = ".jev-review.toml"


@dataclass
class Config:
    mode: str = "block"  # block | advise | off
    subagents: str = "advise"
    max_files: int = 12
    max_total_bytes: int = 60_000
    per_file_bytes: int = 12_000
    prompt_bytes: int = 2_000
    summary_bytes: int = 1_000
    timeout_seconds: float = 45.0
    workers: int = 6
    model: str = "jev-latest"
    thresholds: dict[str, float] = field(default_factory=dict)
    deny_paths: list[str] = field(default_factory=list)
    extra_patterns: list[str] = field(default_factory=list)
    standards: str = "STANDARDS.md"
    state_dir: str = "~/.local/state/jev-review"
    source_files: list[str] = field(default_factory=list)

    def state_root(self) -> Path:
        return Path(self.state_dir).expanduser()


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        return tomllib.load(f)


def load_config(repo_root: Path | None = None, extra: Path | None = None) -> Config:
    """Shipped defaults, then <repo>/.jev-review.toml, then an explicit extra file."""
    raw: dict[str, Any] = {}
    sources: list[str] = []
    for p in [DEFAULT_CONFIG_PATH,
              (repo_root / PROJECT_CONFIG_NAME) if repo_root else None,
              extra]:
        if p and p.is_file():
            raw = _deep_merge(raw, _read_toml(p))
            sources.append(str(p))
    review = raw.get("review", {})
    paths = raw.get("paths", {})
    redact = raw.get("redact", {})
    cfg = Config(
        mode=review.get("mode", "block"),
        subagents=review.get("subagents", "advise"),
        max_files=int(review.get("max_files", 12)),
        max_total_bytes=int(review.get("max_total_bytes", 60_000)),
        per_file_bytes=int(review.get("per_file_bytes", 12_000)),
        prompt_bytes=int(review.get("prompt_bytes", 2_000)),
        summary_bytes=int(review.get("summary_bytes", 1_000)),
        timeout_seconds=float(review.get("timeout_seconds", 45.0)),
        workers=int(review.get("workers", 6)),
        model=review.get("model", "jev-latest"),
        thresholds={k: float(v) for k, v in raw.get("thresholds", {}).items()},
        deny_paths=list(redact.get("deny_paths", [])),
        extra_patterns=list(redact.get("extra_patterns", [])),
        standards=paths.get("standards", "STANDARDS.md"),
        state_dir=paths.get("state_dir", "~/.local/state/jev-review"),
        source_files=sources,
    )
    return cfg


def load_standards(cfg: Config, repo_root: Path | None) -> str:
    """Project STANDARDS.md if present, else the default shipped with the package."""
    if repo_root:
        p = repo_root / cfg.standards
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")
    if DEFAULT_STANDARDS_PATH.is_file():
        return DEFAULT_STANDARDS_PATH.read_text(encoding="utf-8", errors="replace")
    return "No project standards provided."
