"""Tests for concurrent, repository-isolated Git collection."""

from datetime import UTC, datetime
from pathlib import Path

from gitscope.git.clone import RepositoryCheckout
from gitscope.git.collection import collect_git_contributions
from gitscope.git.identities import AuthorIdentities
from gitscope.git.runner import GitCommandError
from gitscope.git.stats import RepositoryCommitAnalysis
from gitscope.models.commit import CommitContribution


def test_collection_continues_when_one_repository_fails(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    from pytest import MonkeyPatch

    assert isinstance(monkeypatch, MonkeyPatch)

    def prepare(repository: str, *_args: object, **_kwargs: object) -> RepositoryCheckout:
        if repository.endswith("broken"):
            raise GitCommandError("access denied")
        return RepositoryCheckout(repository, tmp_path)

    commit = CommitContribution(
        sha="a" * 40,
        repository="org/good",
        authored_at=datetime(2026, 1, 1, tzinfo=UTC),
        additions=2,
        deletions=1,
        files_changed=1,
        is_merge=False,
    )
    monkeypatch.setattr("gitscope.git.collection.prepare_repository", prepare)
    monkeypatch.setattr(
        "gitscope.git.collection.analyze_repository_commits",
        lambda *_args: RepositoryCommitAnalysis("org/good", (commit,), ()),
    )

    result = collect_git_contributions(
        ("org/good", "org/broken"),
        cache_directory=tmp_path,
        token="secret",
        identities=AuthorIdentities(frozenset(), frozenset()),
        concurrency=2,
    )

    assert result.commits == (commit,)
    assert result.repository_analyses[0].repository == "org/good"
    assert result.repositories_processed == 1
    assert result.repositories_failed == 1
    assert result.warnings == ("Could not analyze org/broken: access denied",)
