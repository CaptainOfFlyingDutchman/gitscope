"""Tests for the GitScope CLI."""

from datetime import UTC, datetime

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


def test_analyze_discovers_repositories(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_discovery(
        settings: Settings,
        *,
        refresh: bool = False,
    ) -> DiscoveryContext:
        assert settings.organization == "josys-src"
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
    result = runner.invoke(
        app,
        [
            "analyze",
            "--org",
            "josys-src",
            "--user",
            "CaptainOfFlyingDutchman",
            "--refresh",
        ],
        env={"GITHUB_TOKEN": "secret-token"},
    )

    assert result.exit_code == 0
    assert "Authenticated as octocat" in result.stdout
    assert "Found 0 visible repositories in josys-src" in result.stdout
    assert "4,999" in result.stdout


def test_analyze_reports_github_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def rejected_discovery(
        _settings: Settings,
        *,
        refresh: bool = False,
    ) -> DiscoveryContext:
        del refresh
        raise AuthenticationError("token rejected")

    monkeypatch.setattr("gitscope.cli.discover_repositories", rejected_discovery)
    result = runner.invoke(
        app,
        ["analyze", "--org", "josys-src", "--user", "CaptainOfFlyingDutchman"],
        env={"GITHUB_TOKEN": "secret-token"},
    )

    assert result.exit_code == 1
    assert "GitHub error: token rejected" in result.stderr
