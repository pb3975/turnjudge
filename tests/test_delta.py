"""Delta extraction: untracked, renamed, deleted, binary, over-cap; snapshots never touch the index."""
from pathlib import Path

from turnjudge.delta import EMPTY_TREE, commit_file_delta, commit_files, file_deltas, head_tree, snapshot_tree, turn_files
from turnjudge.redact import redact_diff
from tests.conftest import git


def test_snapshot_includes_untracked_and_respects_gitignore(repo):
    start = snapshot_tree(repo)
    assert start == head_tree(repo)
    (repo / "new.py").write_text("print('hi')\n")
    (repo / "debug.log").write_text("ignored\n")
    end = snapshot_tree(repo)
    assert end != start
    ds = file_deltas(repo, start, end)
    assert [(d.path, d.status) for d in ds] == [("new.py", "A")]
    # the real index is untouched: nothing staged
    assert git(repo, "diff", "--cached", "--name-only").strip() == ""


def test_modified_deleted_renamed_binary(repo):
    start = snapshot_tree(repo)
    (repo / "app.py").write_text("def main():\n    return 2\n")
    (repo / "gone.py").write_text("x = 1\n")
    (repo / "old.py").write_text("y = 2\n" * 20)
    (repo / "pic.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(range(256)))
    git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "setup")
    start = snapshot_tree(repo)
    (repo / "app.py").write_text("def main():\n    return 3\n")
    (repo / "gone.py").unlink()
    (repo / "old.py").rename(repo / "renamed.py")
    (repo / "pic.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(reversed(range(256))))
    git(repo, "add", "-A")  # stage so the rename is detectable in the temp index too
    end = snapshot_tree(repo)
    ds = {d.path: d for d in file_deltas(repo, start, end)}
    assert ds["app.py"].status == "M" and ds["app.py"].judged and "+    return 3" in ds["app.py"].diff
    assert ds["gone.py"].status == "D" and not ds["gone.py"].judged and ds["gone.py"].skip_reason == "deleted"
    assert ds["renamed.py"].status == "R" and ds["renamed.py"].old_path == "old.py" and ds["renamed.py"].skip_reason == "pure-rename"
    assert ds["pic.png"].binary and ds["pic.png"].skip_reason == "binary"
    assert ds["app.py"].lines_added == 1 and ds["app.py"].lines_removed == 1


def test_over_cap_is_truncated_not_dropped(repo):
    start = snapshot_tree(repo)
    (repo / "big.py").write_text("".join(f"x{i} = {i}\n" for i in range(3000)))
    end = snapshot_tree(repo)
    d = file_deltas(repo, start, end)[0]
    r = redact_diff(d.path, d.diff, per_file_bytes=12_000)
    assert r.truncated and len(r.text.encode()) <= 12_100 and "<TRUNCATED" in r.text


def test_unborn_head_tree(tmp_path):
    r = tmp_path / "empty"; r.mkdir(); git(r, "init", "-q")
    assert head_tree(r) == EMPTY_TREE


def test_commit_file_delta_and_turn_files(repo):
    (repo / "app.py").write_text("def main():\n    return 42\n")
    (repo / "test_app.py").write_text("def test():\n    assert True\n")
    git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "change")
    sha = git(repo, "rev-parse", "HEAD").strip()
    d = commit_file_delta(repo, sha, "app.py")
    assert d is not None and "+    return 42" in d.diff and "@@" in d.diff
    tf = turn_files(commit_files(repo, sha))
    assert {t["path"] for t in tf} == {"app.py", "test_app.py"}
    assert commit_file_delta(repo, sha, "missing.py") is None
