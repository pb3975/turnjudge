"""Per-project state dir, session state, audit log, error log."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import traceback
from pathlib import Path
from typing import Any

from turnjudge.config import Config


def project_slug(repo: Path) -> str:
    h = hashlib.sha1(str(repo).encode()).hexdigest()[:8]
    return f"{repo.name}-{h}"


class Store:
    def __init__(self, cfg: Config, repo: Path):
        self.root = cfg.state_root() / project_slug(repo)
        self.sessions = self.root / "sessions"
        self.audit_dir = self.root / "audit"
        for d in (self.sessions, self.audit_dir):
            d.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(cfg.state_root(), 0o700)
        except OSError:
            pass

    # ---- session state ------------------------------------------------------------------
    def session_path(self, session_id: str) -> Path:
        safe = "".join(c for c in session_id if c.isalnum() or c in "-_")[:80] or "unknown"
        return self.sessions / f"{safe}.json"

    def load_session(self, session_id: str) -> dict[str, Any]:
        p = self.session_path(session_id)
        if p.is_file():
            try:
                return json.loads(p.read_text())
            except json.JSONDecodeError:
                return {}
        return {}

    def save_session(self, session_id: str, data: dict[str, Any]) -> None:
        p = self.session_path(session_id)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1))
        os.replace(tmp, p)

    # ---- audit ---------------------------------------------------------------------------
    def audit(self, record: dict[str, Any]) -> Path | None:
        day = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
        p = self.audit_dir / f"{day}.jsonl"
        record = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **record}
        try:
            with p.open("a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except (OSError, TypeError, ValueError) as exc:
            self.log_error("audit", exc)
            return None
        return p

    def audit_files(self) -> list[Path]:
        return sorted(self.audit_dir.glob("*.jsonl"))

    # ---- errors --------------------------------------------------------------------------
    def log_error(self, where: str, exc: BaseException | None = None, note: str = "") -> None:
        p = self.root / "errors.log"
        try:
            self._log_error(p, where, exc, note)
        except OSError:
            pass

    def _log_error(self, p: Path, where: str, exc: BaseException | None, note: str) -> None:
        with p.open("a") as f:
            f.write(f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')} {where} {note}\n")
            if exc is not None:
                f.write("".join(traceback.format_exception(exc)))
