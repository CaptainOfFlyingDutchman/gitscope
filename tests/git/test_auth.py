"""Tests for token-safe Git authentication."""

from pathlib import Path

from gitscope.git.auth import git_auth_environment


def test_git_auth_uses_temporary_askpass_without_embedding_token() -> None:
    with git_auth_environment("top-secret") as environment:
        askpass = Path(environment["GIT_ASKPASS"])

        assert askpass.exists()
        assert "top-secret" not in askpass.read_text(encoding="utf-8")
        assert environment["GIT_TERMINAL_PROMPT"] == "0"
        assert environment["GITSCOPE_GITHUB_TOKEN"] == "top-secret"

    assert not askpass.exists()
