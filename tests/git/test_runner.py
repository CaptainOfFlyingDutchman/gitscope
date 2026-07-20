"""Tests for native Git command failures."""

from pathlib import Path

import pytest

from gitscope.git.runner import GitCommandError, run_git


def test_run_git_returns_stdout(tmp_path: Path) -> None:
    assert run_git(["--version"], cwd=tmp_path).startswith("git version")


def test_run_git_raises_concise_error(tmp_path: Path) -> None:
    with pytest.raises(GitCommandError, match="not a git repository"):
        run_git(["status"], cwd=tmp_path)
