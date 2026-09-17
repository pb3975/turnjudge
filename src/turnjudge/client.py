"""TypeSafe client wrapper: key handling, retries, timeouts, and raw-response recording.

The key is read from TYPESAFE_API_KEY or ~/.config/turnjudge/key (mode 0600). It is never
read from a project directory, never written anywhere, and never logged.
"""

from __future__ import annotations

import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

KEY_ENV = "TYPESAFE_API_KEY"
KEY_FILE = Path("~/.config/turnjudge/key").expanduser()


class KeyError_(Exception):
    """Key missing or unusable. Named to avoid shadowing the builtin."""


def key_file_mode_ok(path: Path = KEY_FILE) -> bool:
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return False
    return mode & 0o077 == 0


def load_key(require_file_mode: bool = True) -> str:
    env = os.environ.get(KEY_ENV, "").strip()
    if env:
        return env
    if not KEY_FILE.is_file():
        raise KeyError_(f"no key: set {KEY_ENV} or create {KEY_FILE}")
    if require_file_mode and not key_file_mode_ok():
        raise KeyError_(f"{KEY_FILE} is group- or world-readable; chmod 600 it")
    key = KEY_FILE.read_text().strip()
    if not key:
        raise KeyError_(f"{KEY_FILE} is empty")
    return key


def key_source() -> str:
    """Where the key comes from, for doctor. Never returns the key."""
    if os.environ.get(KEY_ENV, "").strip():
        return f"env:{KEY_ENV}"
    if KEY_FILE.is_file():
        return f"file:{KEY_FILE}"
    return "none"


@dataclass
class Judgment:
    """One request's outcome: the raw API response body (answers, usage, model) plus timing."""
    raw: dict[str, Any] | None
    error: str | None
    error_kind: str | None  # auth | rate | timeout | connection | api | other
    seconds: float
    request_id: str | None = None

    @property
    def ok(self) -> bool:
        return self.raw is not None and self.error is None


def _classify(exc: BaseException) -> str:
    import typesafe_sdk as t
    if isinstance(exc, t.TypeSafeAuthenticationError):
        return "auth"
    if isinstance(exc, (t.TypeSafeRateLimitError,)):
        return "rate"
    if isinstance(exc, t.TypeSafeAPITimeoutError):
        return "timeout"
    if isinstance(exc, t.TypeSafeAPIConnectionError):
        return "connection"
    if isinstance(exc, t.TypeSafeAPIError):
        status = getattr(exc, "status", None)
        return "rate" if status in (429, 529, 503) else "api"
    return "other"


class JevClient:
    """Thin wrapper so the rest of the code never touches the SDK directly."""

    def __init__(self, *, model: str = "jev-latest", timeout: float = 30.0, max_retries: int = 2,
                 api_key: str | None = None):
        from typesafe_sdk import RetryPolicy, TypeSafeClient
        self.model = model
        self.timeout = timeout
        key = api_key or load_key()
        # RetryPolicy.timeout is the total budget across retries; per-operation timeout is `timeout`.
        self._client = TypeSafeClient(
            api_key=key, model=model,
            retry=RetryPolicy(max_retries=max_retries, backoff_max=2.0, timeout=timeout),
            timeout=min(timeout, 20.0),
        )

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    def __enter__(self) -> "JevClient":
        return self

    def __exit__(self, *a) -> None:
        self.close()

    def judge(self, state: dict[str, Any], questions: dict[str, Any]) -> Judgment:
        t0 = time.monotonic()
        try:
            r = self._client.system_one(state, questions)
        except Exception as e:  # never let an SDK error escape into a hook
            return Judgment(raw=None, error=f"{type(e).__name__}: {str(e)[:200]}", error_kind=_classify(e),
                            seconds=time.monotonic() - t0)
        raw: dict[str, Any]
        try:
            raw = r.raw_http_response.json()
        except Exception:
            raw = {"model": r.model, "answers": {}, "usage": {}}
        # Ensure the typed view and the raw view agree; typed access is what policy uses.
        answers = raw.setdefault("answers", {})
        for qid, a in r.nouls.items():
            answers.setdefault(qid, {"type": "noul", "noul": a.noul})
        for qid, a in r.scores.items():
            answers.setdefault(qid, {"type": "score", "score": a.score, "confidence": a.confidence,
                                     "probabilities": {str(k): v for k, v in a.probabilities.items()},
                                     "legend": {str(k): v for k, v in a.legend.items()}})
        usage = raw.setdefault("usage", {})
        usage.setdefault("input_tokens", r.usage.input_tokens)
        usage.setdefault("output_tokens", r.usage.output_tokens)
        usage.setdefault("billing_units", None)  # SDK 0.6.0: the API does not return billing_units
        raw.setdefault("model", r.model)
        return Judgment(raw=raw, error=None, error_kind=None, seconds=time.monotonic() - t0,
                        request_id=getattr(r, "request_id", None))


# ---- Offline fake for tests and dry runs ------------------------------------------------------

FAKE_ENV = "TURNJUDGE_FAKE"


class FakeClient:
    """Stands in for JevClient when TURNJUDGE_FAKE is set.

    TURNJUDGE_FAKE=<path.json>   answers come from that file: {"default": {...answers...},
                                  "by_path": {"src/x.py": {...answers...}}}
    TURNJUDGE_FAKE=error:<kind>  every judge() fails with that error kind (auth|rate|timeout|connection)
    TURNJUDGE_FAKE=sleep:<sec>   every judge() sleeps that long, then answers "all clear"
    """

    def __init__(self, spec: str):
        import json
        self.spec = spec
        self.error_kind: str | None = None
        self.sleep = 0.0
        self.answers: dict[str, Any] = {"default": {}, "by_path": {}}
        if spec.startswith("error:"):
            self.error_kind = spec.split(":", 1)[1]
        elif spec.startswith("sleep:"):
            self.sleep = float(spec.split(":", 1)[1])
        elif spec:
            self.answers = json.loads(Path(spec).read_text())

    def close(self) -> None:
        pass

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *a) -> None:
        pass

    def judge(self, state: dict[str, Any], questions: dict[str, Any]) -> Judgment:
        if self.error_kind:
            return Judgment(raw=None, error=f"fake {self.error_kind}", error_kind=self.error_kind, seconds=0.0)
        if self.sleep:
            time.sleep(self.sleep)
        path = (state.get("file") or {}).get("path", "")
        answers = dict(self.answers.get("default", {}))
        answers.update(self.answers.get("by_path", {}).get(path, {}))
        return Judgment(raw={"model": "fake", "answers": answers,
                             "usage": {"input_tokens": 0, "output_tokens": 0, "billing_units": None}},
                        error=None, error_kind=None, seconds=0.0, request_id="fake")


def make_client(*, model: str, timeout: float):
    spec = os.environ.get(FAKE_ENV)
    if spec is not None:
        return FakeClient(spec)
    return JevClient(model=model, timeout=timeout)
