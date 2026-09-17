"""Redaction: deny lists, secret patterns, identity trimming, and size caps.

Runs on every diff before anything is sent. Nothing leaves the machine unredacted, uncapped,
or unlogged. Each rule here has a test in tests/test_redact.py.
"""

from __future__ import annotations

import fnmatch
import math
import os
import re
import socket
from dataclasses import dataclass, field
from pathlib import PurePosixPath

# ---- Deny list: files never sent ------------------------------------------------------------

DENY_GLOBS = [
    ".env", ".env.*", "*.env",
    "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "*.keystore",
    "id_*", "*.ppk",
    "*secrets*", "*credentials*", "*credential*",
    "*.min.*",
    # lockfiles
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "bun.lock",
    "uv.lock", "poetry.lock", "Pipfile.lock", "requirements*.lock",
    "Cargo.lock", "go.sum", "composer.lock", "Gemfile.lock", "mix.lock",
    "flake.lock", "packages.lock.json", "*.lock",
]

GENERATED_HINTS = [
    "*.generated.*", "*_generated.*", "*.pb.go", "*_pb2.py", "*.pb.ts", "*.d.ts.map", "*.map",
    "dist/**", "build/**", "node_modules/**", "vendor/**", "__snapshots__/**",
]

BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".tar", ".tgz",
    ".bz2", ".xz", ".7z", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".mp3", ".mp4", ".mov",
    ".wav", ".so", ".dylib", ".dll", ".exe", ".bin", ".pyc", ".class", ".jar", ".wasm", ".sqlite",
    ".db", ".parquet",
}


def _matches(path: str, pattern: str) -> bool:
    p = PurePosixPath(path)
    if "/" in pattern or "**" in pattern:
        # path-style pattern: match against the full relative path
        regex = fnmatch.translate(pattern.replace("**/", "*/").replace("/**", "/*"))
        if fnmatch.fnmatch(path, pattern):
            return True
        # allow "dir/**" to match "dir/x/y"
        if pattern.endswith("/**") and path.startswith(pattern[:-3] + "/"):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(p.name, pattern[3:]):
            return True
        return re.match(regex, path) is not None
    return fnmatch.fnmatch(p.name.lower(), pattern.lower())


def deny_reason(path: str, extra_deny_paths: list[str] | None = None) -> str | None:
    """Why this file must be withheld entirely, or None if it may be sent (after scrubbing)."""
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    lower = path.lower()
    for g in DENY_GLOBS:
        if _matches(lower, g.lower()):
            return f"deny-list:{g}"
    for g in extra_deny_paths or []:
        if _matches(path, g):
            return f"deny-path:{g}"
    for g in GENERATED_HINTS:
        if _matches(lower, g):
            return f"generated:{g}"
    if PurePosixPath(lower).suffix in BINARY_EXT:
        return "binary"
    return None


# ---- Secret patterns: replaced with <REDACTED:kind> ------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private_key", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----|"
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*$")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA)[A-Z0-9]{16}\b")),
    ("aws_secret_key", re.compile(
        r"(?i)(aws[_-]?secret[_-]?access[_-]?key|aws[_-]?secret)\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("gitlab_token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("slack_webhook", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]+")),
    ("stripe_key", re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("openai_style_key", re.compile(r"\bsk-(?:proj-|ant-|or-v1-)?[A-Za-z0-9_-]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("sendgrid_key", re.compile(r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b")),
    ("npm_token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("azure_storage_key", re.compile(r"(?i)(AccountKey)\s*=\s*([A-Za-z0-9+/]{86}==)")),
    ("twilio_sid", re.compile(r"\bAC[0-9a-fA-F]{32}\b")),
    ("pypi_token", re.compile(r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{20,}\b")),
    ("apikey_prefix", re.compile(r"\b(?:apikey|api_key|apik)_[A-Za-z0-9]{16,}\b", re.IGNORECASE)),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("bearer", re.compile(r"(?i)(authorization\s*[:=]\s*['\"]?bearer\s+|\bbearer\s+)([A-Za-z0-9._~+/=-]{16,})")),
    ("basic_auth_header", re.compile(r"(?i)(authorization\s*[:=]\s*['\"]?basic\s+)([A-Za-z0-9+/=]{12,})")),
    ("url_userinfo", re.compile(r"\b([a-z][a-z0-9+.-]*://)([^/\s:@'\"]*):([^/\s@'\"]+)@")),
    ("password_assignment", re.compile(
        r"(?i)\b(password|passwd|pwd|secret|client_secret|token|api_key|apikey|access_key|auth_token|private_key)"
        r"\s*[=:]\s*['\"]([^'\"\s]{8,})['\"]")),
]

_ASSIGN_CONTEXT = re.compile(
    r"(?i)([A-Za-z_][A-Za-z0-9_.-]*\s*[=:]\s*|-H\s+['\"]?[A-Za-z-]+:\s*|\b[A-Za-z-]+:\s+)['\"]?([A-Za-z0-9+/=_.\-]{32,})['\"]?")

_PLACEHOLDER_HINTS = re.compile(r"(?i)(example|placeholder|your[_-]|xxx|redacted|dummy|changeme|<[^>]+>|\$\{|\{\{)")


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts: dict[str, int] = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def _looks_like_hex_or_hash(s: str) -> bool:
    return re.fullmatch(r"[0-9a-f]{32,}", s.lower()) is not None


ENTROPY_THRESHOLD = 4.2


def scrub_secrets(text: str, extra_patterns: list[str] | None = None) -> tuple[str, dict[str, int]]:
    """Replace secret-looking substrings. Returns (scrubbed, counts by kind)."""
    counts: dict[str, int] = {}

    def bump(kind: str) -> str:
        counts[kind] = counts.get(kind, 0) + 1
        return f"<REDACTED:{kind}>"

    for kind, pat in _PATTERNS:
        if kind in ("bearer", "basic_auth_header"):
            text = pat.sub(lambda m: m.group(1) + bump(kind), text)
        elif kind == "url_userinfo":
            text = pat.sub(lambda m: m.group(1) + bump(kind) + "@", text)
        elif kind == "password_assignment":
            def _pw(m: re.Match[str]) -> str:
                val = m.group(2)
                if _PLACEHOLDER_HINTS.search(val):
                    return m.group(0)
                return m.group(0).replace(val, bump("assigned_secret"))
            text = pat.sub(_pw, text)
        elif kind in ("aws_secret_key", "azure_storage_key"):
            text = pat.sub(lambda m: m.group(0).replace(m.group(2), bump(kind)), text)
        else:
            text = pat.sub(lambda m: bump(kind), text)

    for extra in extra_patterns or []:
        try:
            text = re.sub(extra, lambda m: bump("custom"), text)
        except re.error:
            continue

    # High-entropy strings in assignment or header context
    def _entropy_sub(m: re.Match[str]) -> str:
        val = m.group(2)
        if "REDACTED" in val or _PLACEHOLDER_HINTS.search(val):
            return m.group(0)
        if _looks_like_hex_or_hash(val) and len(val) in (32, 40, 64):
            # sha1/sha256/md5 digests are common in lockfiles and tests; leave them
            return m.group(0)
        if shannon_entropy(val) >= ENTROPY_THRESHOLD:
            return m.group(0).replace(val, bump("high_entropy"))
        return m.group(0)

    text = _ASSIGN_CONTEXT.sub(_entropy_sub, text)
    return text, counts


# ---- Identity trimming ---------------------------------------------------------------------

def _identity_patterns() -> list[tuple[re.Pattern[str], str]]:
    pats: list[tuple[re.Pattern[str], str]] = []
    home = os.path.expanduser("~")
    if home and home != "~":
        pats.append((re.compile(re.escape(home)), "~"))
        user = os.path.basename(home)
        if user:
            pats.append((re.compile(r"/(?:home|Users)/" + re.escape(user) + r"\b"), "~"))
    try:
        host = socket.gethostname()
    except Exception:
        host = ""
    if host and len(host) > 2:
        pats.append((re.compile(r"\b" + re.escape(host) + r"\b"), "<HOST>"))
    for var in ("GIT_AUTHOR_EMAIL", "EMAIL", "JEV_REVIEW_USER_EMAIL"):
        v = os.environ.get(var)
        if v and "@" in v:
            pats.append((re.compile(re.escape(v)), "<EMAIL>"))
    return pats


_IDENTITY_CACHE: list[tuple[re.Pattern[str], str]] | None = None


def trim_identity(text: str, emails: list[str] | None = None) -> str:
    global _IDENTITY_CACHE
    if _IDENTITY_CACHE is None:
        _IDENTITY_CACHE = _identity_patterns()
    for pat, rep in _IDENTITY_CACHE:
        text = pat.sub(rep, text)
    for e in emails or []:
        if e:
            text = text.replace(e, "<EMAIL>")
    return text


# ---- Caps ---------------------------------------------------------------------------------

def cap(text: str, limit: int, label: str = "diff") -> tuple[str, bool]:
    if len(text.encode("utf-8")) <= limit:
        return text, False
    b = text.encode("utf-8")[:limit]
    cut = b.decode("utf-8", errors="ignore")
    cut = cut[: cut.rfind("\n")] if "\n" in cut else cut
    return cut + f"\n<TRUNCATED: {label} exceeded {limit} bytes>", True


# ---- Whole-file redaction --------------------------------------------------------------------

@dataclass
class Redacted:
    text: str
    withheld_reason: str | None = None
    truncated: bool = False
    counts: dict[str, int] = field(default_factory=dict)


def redact_diff(path: str, diff: str, *, per_file_bytes: int, extra_deny_paths: list[str] | None = None,
                extra_patterns: list[str] | None = None, emails: list[str] | None = None) -> Redacted:
    reason = deny_reason(path, extra_deny_paths)
    if reason:
        return Redacted(text="", withheld_reason=reason)
    scrubbed, counts = scrub_secrets(diff, extra_patterns)
    scrubbed = trim_identity(scrubbed, emails)
    capped, truncated = cap(scrubbed, per_file_bytes, "diff")
    return Redacted(text=capped, truncated=truncated, counts=counts)


def redact_text(text: str, limit: int, label: str, emails: list[str] | None = None) -> str:
    scrubbed, _ = scrub_secrets(text)
    scrubbed = trim_identity(scrubbed, emails)
    capped, _ = cap(scrubbed, limit, label)
    return capped
