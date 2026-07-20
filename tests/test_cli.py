"""Tests for the GitScope CLI."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from gitscope import __version__
from gitscope.cli import app
from gitscope.config import Settings
from gitscope.github.discovery import DiscoveryContext
from gitscope.github.errors import AuthenticationError
from gitscope.github.models import AuthenticatedUser, RateLimit, RepositoryDiscovery

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"GitScope {__version__}" in result.stdout


def test_analyze_requires_token() -> None:
    result = runner.invoke(
        app,
        ["analyze", "--org", "josys-src", "--user", "CaptainOfFlyingDutchman"],
        env={"GITHUB_TOKEN": ""},
    )

    assert result.exit_code == 2
    assert "GITHUB_TOKEN is not configured" in result.stderr


def test_analyze_discovers_repositories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def fake_discovery(
        settings: Settings,
        repository_names: tuple[str, ...],
        *,
        refresh: bool = False,
    ) -> DiscoveryContext:
        assert settings.organization == "josys-src"
        assert repository_names == ("frontend",)
        assert refresh is True
        return DiscoveryContext(
            authenticated_user=AuthenticatedUser(login="octocat", id=1),
            discovery=RepositoryDiscovery(
                repositories=(),
                source="graphql",
                rate_limit=RateLimit(
                    cost=1,
                    remaining=4999,
                    resetAt=datetime(2026, 7, 20, tzinfo=UTC),
                ),
            ),
        )

    monkeypatch.setattr("gitscope.cli.discover_repositories", fake_discovery)
    repositories_file = tmp_path / "repositories"
    repositories_file.write_text("josys-src/frontend\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "analyze",
            "--org",
            "josys-src",
            "--user",
            "CaptainOfFlyingDutchman",
            "--refresh",
            "--repos-file",
            str(repositories_file),
        ],
        env={"GITHUB_TOKEN": "secret-token"},
    )

    assert result.exit_code == 0
    assert "Authenticated as octocat" in result.stdout
    assert "Validated 0 allowlisted repositories in josys-src" in result.stdout
    assert "4,999" in result.stdout


def test_analyze_reports_github_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def rejected_discovery(
        _settings: Settings,
        _repository_names: tuple[str, ...],
        *,
        refresh: bool = False,
    ) -> DiscoveryContext:
        del refresh
        raise AuthenticationError("token rejected")

    monkeypatch.setattr("gitscope.cli.discover_repositories", rejected_discovery)
    repositories_file = tmp_path / "repositories"
    repositories_file.write_text("josys-src/frontend\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "analyze",
            "--org",
            "josys-src",
            "--user",
            "CaptainOfFlyingDutchman",
            "--repos-file",
            str(repositories_file),
        ],
        env={"GITHUB_TOKEN": "secret-token"},
    )

    assert result.exit_code == 1
    assert "GitHub error: token rejected" in result.stderr


def test_analyze_requires_repository_file(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "analyze",
            "--org",
            "josys-src",
            "--user",
            "CaptainOfFlyingDutchman",
            "--repos-file",
            str(tmp_path / "missing"),
        ],
        env={"GITHUB_TOKEN": "secret-token"},
    )

    assert result.exit_code == 2
    assert "Repository list error" in result.stderr
