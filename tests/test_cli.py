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
from gitscope.models.report import (
    CareerReport,
    CollectionMetadata,
    CommitSummary,
    LanguageSummary,
    PullRequestSummary,
    ReportIdentity,
    ReviewSummary,
    TimelineSummary,
)
from gitscope.report.generate import GeneratedCareerReport
from gitscope.repository_scope import RepositoryScope

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


def test_analyze_generates_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def fake_generation(
        settings: Settings,
        repository_scope: RepositoryScope,
        *,
        refresh: bool = False,
        rate_limit_reserve: int = 500,
        identities_file: Path = Path(".gitscope-identities"),
        git_concurrency: int = 4,
    ) -> GeneratedCareerReport:
        assert settings.organization == "josys-src"
        assert repository_scope.names == ("frontend",)
        assert refresh is True
        assert rate_limit_reserve == 500
        assert identities_file == Path(".gitscope-identities")
        assert git_concurrency == 4
        context = DiscoveryContext(
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
        report = CareerReport(
            organization="josys-src",
            identity=ReportIdentity(username="target", authenticated_as="octocat"),
            collection=CollectionMetadata(
                generated_at=datetime(2026, 7, 20, tzinfo=UTC),
                repository_scope_file=str(repository_scope.source),
                repository_count=0,
                github_api_requests=1,
                github_cache_hits=0,
                graphql_rate_limit_remaining=4999,
            ),
            repositories=(),
            repository_analytics=(),
            language_summary=LanguageSummary(
                primary_repository_languages={},
                contributed_languages=(),
                file_extensions=(),
            ),
            timeline=TimelineSummary(
                first_contribution=None,
                last_contribution=None,
                career_span_days=0,
                active_days=0,
                monthly_activity=(),
                yearly_activity=(),
                most_active_month=None,
                most_active_year=None,
                milestones=(),
            ),
            commit_summary=CommitSummary(
                total=0,
                additions=0,
                deletions=0,
                files_changed=0,
                merge_commits=0,
                first_contribution=None,
                last_contribution=None,
                by_repository={},
                by_year={},
                by_month={},
                by_weekday={},
                by_hour={},
            ),
            pull_request_summary=PullRequestSummary(
                total=0,
                open=0,
                closed=0,
                merged=0,
                drafts=0,
                merge_rate=None,
            ),
            review_summary=ReviewSummary(
                total=0,
                approvals=0,
                changes_requested=0,
                comments=0,
                dismissed=0,
            ),
            pull_requests=(),
            reviews=(),
            commits=(),
        )
        return GeneratedCareerReport(
            report=report,
            path=tmp_path / "report.json",
            discovery_context=context,
        )

    monkeypatch.setattr("gitscope.cli.generate_career_report", fake_generation)
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
    assert "Collected 0 authored commits, 0 authored pull requests, and 0 submitted reviews" in (
        result.stdout
    )
    assert "0 inferred languages" in result.stdout
    assert "0 days with 0 career milestones" in result.stdout
    assert "4,999" in result.stdout
    assert "report.json" in result.stdout


def test_analyze_reports_github_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def rejected_generation(
        _settings: Settings,
        _repository_scope: RepositoryScope,
        *,
        refresh: bool = False,
        rate_limit_reserve: int = 500,
        identities_file: Path = Path(".gitscope-identities"),
        git_concurrency: int = 4,
    ) -> GeneratedCareerReport:
        del refresh
        del rate_limit_reserve
        del identities_file
        del git_concurrency
        raise AuthenticationError("token rejected")

    monkeypatch.setattr("gitscope.cli.generate_career_report", rejected_generation)
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
