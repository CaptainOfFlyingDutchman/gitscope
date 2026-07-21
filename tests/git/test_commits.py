"""Integration tests against a local Git history."""

import subprocess
from datetime import date
from pathlib import Path

from gitscope.date_range import DateRange
from gitscope.git.commits import analyze_repository_commits
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

    analysis = analyze_repository_commits("org/repo", tmp_path, identities)
    commits = analysis.commits

    assert len(commits) == 1
    assert commits[0].repository == "org/repo"
    assert commits[0].additions == 2
    assert commits[0].deletions == 0
    assert commits[0].files_changed == 1
    assert commits[0].is_merge is False
    assert len(analysis.file_changes) == 1
    assert analysis.file_changes[0].extension == ".txt"
    assert analysis.file_changes[0].language == "Text"
    assert analysis.file_changes[0].additions == 2

    excluded = analyze_repository_commits(
        "org/repo",
        tmp_path,
        identities,
        DateRange(until=date(2020, 12, 31)),
    )
    assert excluded.commits == ()
    assert excluded.file_changes == ()
