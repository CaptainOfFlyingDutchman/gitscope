"""Tests for repository cache preparation."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

import pytest

from gitscope.git.clone import prepare_repository
from gitscope.git.runner import GitCommandError


@contextmanager
def fake_auth(_token: str) -> Iterator[Mapping[str, str]]:
    yield {}


def test_prepare_repository_clones_with_safe_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[list[str], Path | None]] = []

    def run(arguments: list[str], *, cwd: Path | None = None, **_kwargs: object) -> str:
        calls.append((arguments, cwd))
        return ""

    monkeypatch.setattr("gitscope.git.clone.git_auth_environment", fake_auth)
    monkeypatch.setattr("gitscope.git.clone.run_git", run)

    checkout = prepare_repository("org/repo", tmp_path / "cache", "secret")

    assert checkout.path == tmp_path / "cache/repositories/org/repo.git"
    assert calls == [
        (
            [
                "clone",
                "--bare",
                "https://github.com/org/repo.git",
                str(checkout.path),
            ],
            None,
        )
    ]
    assert "secret" not in repr(calls)


def test_prepare_repository_rejects_invalid_name(tmp_path: Path) -> None:
    with pytest.raises(GitCommandError, match="invalid repository"):
        prepare_repository("invalid", tmp_path, "secret")


def test_prepare_repository_bulk_hydrates_an_existing_partial_clone(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "cache/repositories/org/repo.git"
    destination.mkdir(parents=True)
    (destination / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    calls: list[list[str]] = []

    def run(arguments: list[str], **_kwargs: object) -> str:
        calls.append(arguments)
        if arguments[:3] == ["remote", "get-url", "origin"]:
            return "https://github.com/org/repo.git\n"
        if arguments[:3] == ["config", "--get", "remote.origin.promisor"]:
            return "true\n"
        return ""

    monkeypatch.setattr("gitscope.git.clone.git_auth_environment", fake_auth)
    monkeypatch.setattr("gitscope.git.clone.run_git", run)

    prepare_repository("org/repo", tmp_path / "cache", "secret")

    assert [
        "fetch",
        "--prune",
        "--tags",
        "--refetch",
        "--no-filter",
        "origin",
        "+refs/heads/*:refs/heads/*",
    ] in calls
    assert calls[-2:] == [
        ["config", "--unset", "remote.origin.promisor"],
        ["config", "--unset", "remote.origin.partialclonefilter"],
    ]
