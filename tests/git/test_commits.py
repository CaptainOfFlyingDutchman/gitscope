"""Integration tests against a local Git history."""

import subprocess
from pathlib import Path

from gitscope.git.commits import collect_repository_commits
from gitscope.git.identities import AuthorIdentities


def git(path: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=path, check=True, capture_output=True)


def test_collect_repository_commits_matches_identity_and_numstat(tmp_path: Path) -> None:
    git(tmp_path, "init")
    git(tmp_path, "config", "user.name", "Target Author")
    git(tmp_path, "config", "user.email", "target@example.com")
    tracked = tmp_path / "example.txt"
    tracked.write_text("one\ntwo\n", encoding="utf-8")
    git(tmp_path, "add", "example.txt")
    git(tmp_path, "commit", "-m", "target commit")
    git(tmp_path, "config", "user.name", "Someone Else")
    git(tmp_path, "config", "user.email", "else@example.com")
    tracked.write_text("one\ntwo\nthree\n", encoding="utf-8")
    git(tmp_path, "commit", "-am", "other commit")
    identities = AuthorIdentities(
        names=frozenset(),
        emails=frozenset({"target@example.com"}),
    )

    commits = collect_repository_commits("org/repo", tmp_path, identities)

    assert len(commits) == 1
    assert commits[0].repository == "org/repo"
    assert commits[0].additions == 2
    assert commits[0].deletions == 0
    assert commits[0].files_changed == 1
    assert commits[0].is_merge is False
