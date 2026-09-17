"""Turn snapshot and per-file diff extraction.

The unit of review is the turn's delta: the working tree at the end of the turn compared to
the working tree at the start (recorded by `mark`), never the diff against HEAD unless there
is no mark. Snapshots are tree objects written with a temporary index, so the real index is
never touched.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

LANGUAGE_BY_EXT = {
    ".go": "go", ".py": "python", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript",
    ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".svelte": "svelte", ".vue": "vue",
    ".rs": "rust", ".java": "java", ".kt": "kotlin", ".rb": "ruby", ".php": "php", ".cs": "csharp",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp", ".swift": "swift", ".sh": "shell",
    ".bash": "shell", ".zsh": "shell", ".sql": "sql", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".json": "json", ".md": "markdown", ".html": "html", ".css": "css", ".scss": "scss", ".ex": "elixir",
    ".exs": "elixir", ".hs": "haskell", ".scala": "scala", ".lua": "lua", ".dart": "dart", ".zig": "zig",
}

CODE_LANGS = {"go", "python", "typescript", "javascript", "svelte", "vue", "rust", "java", "kotlin", "ruby",
              "php", "csharp", "c", "cpp", "swift", "shell", "sql", "elixir", "haskell", "scala", "lua",
              "dart", "zig"}


class GitError(RuntimeError):
    pass


def git(repo: Path, *args: str, env: dict[str, str] | None = None, check: bool = True, timeout: float = 30) -> str:
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        r = subprocess.run(["git", *args], cwd=str(repo), env=e, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
    except FileNotFoundError as ex:
        raise GitError("git is not installed") from ex
    except subprocess.TimeoutExpired as ex:
        raise GitError(f"git {args[0]} timed out") from ex
    if check and r.returncode != 0:
        raise GitError(f"git {' '.join(args[:2])} failed: {r.stderr.strip()[:300]}")
    return r.stdout


def repo_root(cwd: Path) -> Path | None:
    try:
        out = git(cwd, "rev-parse", "--show-toplevel")
    except GitError:
        return None
    out = out.strip()
    return Path(out) if out else None


def snapshot_tree(repo: Path) -> str:
    """Write a tree object for the working tree (respecting .gitignore) without touching the index."""
    real_index = git(repo, "rev-parse", "--git-path", "index").strip()
    real_index_path = Path(real_index) if os.path.isabs(real_index) else repo / real_index
    with tempfile.TemporaryDirectory(prefix="jev-review-") as td:
        tmp_index = Path(td) / "index"
        if real_index_path.exists():
            tmp_index.write_bytes(real_index_path.read_bytes())
        env = {"GIT_INDEX_FILE": str(tmp_index)}
        git(repo, "add", "-A", "--", ".", env=env)
        return git(repo, "write-tree", env=env).strip()


def head_tree(repo: Path) -> str:
    try:
        return git(repo, "rev-parse", "HEAD^{tree}").strip()
    except GitError:
        return EMPTY_TREE  # unborn branch


def language_for(path: str) -> str:
    return LANGUAGE_BY_EXT.get(Path(path).suffix.lower(), "other")


def repo_language(repo: Path) -> str:
    """Majority code language among tracked files, cheap and good enough for the state."""
    try:
        files = git(repo, "ls-files").splitlines()
    except GitError:
        return "unknown"
    counts: dict[str, int] = {}
    for f in files:
        lang = language_for(f)
        if lang in CODE_LANGS:
            counts[lang] = counts.get(lang, 0) + 1
    return max(counts, key=counts.get) if counts else "unknown"


@dataclass
class FileDelta:
    path: str
    status: str  # A, M, D, R, T ...
    old_path: str | None = None
    diff: str = ""
    lines_added: int = 0
    lines_removed: int = 0
    binary: bool = False
    language: str = "other"
    judged: bool = True
    skip_reason: str | None = None

    def is_code(self) -> bool:
        return self.language in CODE_LANGS


_FILE_HEADER = re.compile(r"^diff --git a/(.*?) b/(.*?)$", re.MULTILINE)


def _split_per_file(raw: str) -> list[tuple[str, str, str]]:
    """Split a multi-file unified diff into (old_path, new_path, text) chunks."""
    positions = [(m.start(), m.group(1), m.group(2)) for m in _FILE_HEADER.finditer(raw)]
    out = []
    for i, (start, a, b) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(raw)
        out.append((a, b, raw[start:end]))
    return out


def _numstat(repo: Path, start: str, end: str, paths: list[str] | None = None) -> dict[str, tuple[int, int, bool]]:
    args = ["diff", "--numstat", "-M", start, end]
    if paths:
        args += ["--", *paths]
    stats: dict[str, tuple[int, int, bool]] = {}
    for line in git(repo, *args).splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        a, r, p = parts[0], parts[1], parts[-1]
        if "=>" in p and "{" in p:  # rename in numstat form "dir/{old => new}"
            p = re.sub(r"\{.*? => (.*?)\}", r"\1", p)
        elif " => " in p:
            p = p.split(" => ")[-1]
        binary = a == "-" or r == "-"
        stats[p] = (0 if binary else int(a), 0 if binary else int(r), binary)
    return stats


def _status(repo: Path, start: str, end: str, paths: list[str] | None = None) -> dict[str, tuple[str, str | None]]:
    args = ["diff", "--name-status", "-M", start, end]
    if paths:
        args += ["--", *paths]
    out: dict[str, tuple[str, str | None]] = {}
    for line in git(repo, *args).splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            out[parts[1]] = (parts[0][0], None)
        elif len(parts) == 3:
            out[parts[2]] = (parts[0][0], parts[1])
    return out


def file_deltas(repo: Path, start: str, end: str, paths: list[str] | None = None,
                context: int = 10, function_context: bool = True) -> list[FileDelta]:
    """Per-file unified diffs between two tree-ish objects (commits or trees)."""
    status = _status(repo, start, end, paths)
    stats = _numstat(repo, start, end, paths)
    args = ["diff", "-M", f"--unified={context}", "--no-color", "--no-ext-diff"]
    if function_context:
        args.append("--function-context")
    args += [start, end]
    if paths:
        args += ["--", *paths]
    raw = git(repo, *args, timeout=60)
    chunks = {b: (a, text) for a, b, text in _split_per_file(raw)}
    deltas: list[FileDelta] = []
    for path, (st, old) in status.items():
        a, r, binary = stats.get(path, (0, 0, False))
        old_path, text = chunks.get(path, (old, ""))
        d = FileDelta(path=path, status=st, old_path=old if st == "R" else None, diff=text,
                      lines_added=a, lines_removed=r, binary=binary or "Binary files" in text[:2000],
                      language=language_for(path))
        if d.binary:
            d.judged, d.skip_reason = False, "binary"
        elif st == "D":
            d.judged, d.skip_reason = False, "deleted"
        elif st == "R" and a == 0 and r == 0:
            d.judged, d.skip_reason = False, "pure-rename"
        deltas.append(d)
    return deltas


def turn_files(deltas: list[FileDelta], limit: int = 40) -> list[dict]:
    """Compact list of every file the turn touched, so per-file questions can see siblings (e.g. tests)."""
    out = [{"path": d.path, "status": d.status, "lines_added": d.lines_added, "lines_removed": d.lines_removed}
           for d in deltas[:limit]]
    if len(deltas) > limit:
        out.append({"path": f"... and {len(deltas) - limit} more files", "status": "", "lines_added": 0, "lines_removed": 0})
    return out


def commit_files(repo: Path, sha: str) -> list[FileDelta]:
    """All file deltas of a commit against its first parent, without diff text."""
    parents = git(repo, "rev-list", "--parents", "-n", "1", sha).split()
    parent = parents[1] if len(parents) > 1 else EMPTY_TREE
    return file_deltas(repo, parent, sha, context=0, function_context=False)


def commit_message(repo: Path, sha: str) -> tuple[str, str]:
    subject = git(repo, "log", "-1", "--format=%s", sha).strip()
    body = git(repo, "log", "-1", "--format=%b", sha).strip()
    return subject, body


def commit_file_delta(repo: Path, sha: str, path: str, **kw) -> FileDelta | None:
    """Reconstruct one file's delta at a commit (against its first parent)."""
    parents = git(repo, "rev-list", "--parents", "-n", "1", sha).split()
    parent = parents[1] if len(parents) > 1 else EMPTY_TREE
    ds = file_deltas(repo, parent, sha, [path], **kw)
    for d in ds:
        if d.path == path:
            return d
    return None


def list_commits(repo: Path, rev_range: str, max_count: int | None = None) -> list[dict]:
    args = ["log", "--no-merges", "--format=%H%x00%s%x00%ad", "--date=short"]
    if max_count:
        args.append(f"-n{max_count}")
    args.append(rev_range)
    out = []
    for line in git(repo, *args).splitlines():
        parts = line.split("\x00")
        if len(parts) == 3:
            out.append({"sha": parts[0], "subject": parts[1], "date": parts[2]})
    return out
