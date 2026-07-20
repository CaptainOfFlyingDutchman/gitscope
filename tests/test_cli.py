"""Tests for the GitScope CLI."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

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


def test_resume_generates_offline_portfolio(tmp_path: Path) -> None:
    from tests.report.test_json import empty_report

    report_path = tmp_path / "report.json"
    report_path.write_text(empty_report().model_dump_json(), encoding="utf-8")
    with patch("gitscope.cli.logger.info") as log_info:
        result = runner.invoke(
            app,
            [
                "resume",
                "--report",
                str(report_path),
                "--name",
                "Manvendra Singh",
                "--title",
                "Staff Engineer",
                "--company",
                "Josys",
                "--site",
                "https://www.manvendrask.com/about",
            ],
            env={"GITHUB_TOKEN": ""},
        )

    assert result.exit_code == 0
    assert "Manvendra Singh" in result.stdout
    assert "Staff Engineer" in result.stdout
    assert "resume.md" in result.stdout
    assert "resume.html" in result.stdout
    assert (tmp_path / "resume.md").exists()
    assert (tmp_path / "resume.html").exists()
    log_info.assert_called_once_with("Resume generation completed: outputs=2")


def test_resume_reports_missing_json(tmp_path: Path) -> None:
    with patch("gitscope.cli.logger.warning") as log_warning:
        result = runner.invoke(app, ["resume", "--report", str(tmp_path / "missing.json")])

    assert result.exit_code == 2
    assert "Resume error" in result.stderr
    log_warning.assert_called_once_with("Resume generation failed: %s", "ResumeError")


def test_cache_path_logs_display_without_exposing_path(tmp_path: Path) -> None:
    cache_directory = tmp_path / "private-cache"

    with patch("gitscope.cli.logger.info") as log_info:
        result = runner.invoke(
            app,
            ["cache", "path", "--cache-dir", str(cache_directory)],
        )

    assert result.exit_code == 0
    assert cache_directory.name in result.stdout
    log_info.assert_called_once_with("Cache path displayed")


def test_export_html_regenerates_dashboard_without_credentials(tmp_path: Path) -> None:
    from tests.report.test_json import empty_report

    report_path = tmp_path / "source" / "report.json"
    report_path.parent.mkdir()
    report_path.write_text(empty_report().model_dump_json(), encoding="utf-8")
    output_directory = tmp_path / "exported"

    result = runner.invoke(
        app,
        [
            "export",
            "html",
            "--report",
            str(report_path),
            "--output",
            str(output_directory),
        ],
        env={"GITHUB_TOKEN": ""},
    )

    assert result.exit_code == 0
    assert "Loaded GitScope schema 1.5" in result.stdout
    assert "Contribution summary" in result.stdout
    assert "no GitHub API or Git repository access" in result.stdout
    assert (output_directory / "report.html").exists()
    assert (output_directory / "charts" / "plotly.min.js").exists()


def test_export_reports_missing_json(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["export", "csv", "--report", str(tmp_path / "missing.json")],
    )

    assert result.exit_code == 2
    assert "Export error" in result.stderr


def test_cache_status_and_clear_are_scoped(tmp_path: Path) -> None:
    cache_directory = tmp_path / "cache"
    graphql = cache_directory / "graphql"
    repository = cache_directory / "repositories" / "org" / "repo.git"
    graphql.mkdir(parents=True)
    repository.mkdir(parents=True)
    (graphql / "entry.json").write_text("payload", encoding="utf-8")
    (repository / "HEAD").write_text("ref", encoding="utf-8")

    status_result = runner.invoke(
        app,
        ["cache", "status", "--cache-dir", str(cache_directory)],
    )
    clear_result = runner.invoke(
        app,
        ["cache", "clear", "graphql", "--cache-dir", str(cache_directory), "--yes"],
    )

    assert status_result.exit_code == 0
    assert "GitScope cache" in status_result.stdout
    assert "repository names are not displayed" in status_result.stdout
    assert clear_result.exit_code == 0
    assert "Cleared graphql" in clear_result.stdout
    assert not graphql.exists()
    assert repository.exists()


def test_cache_clear_can_be_cancelled(tmp_path: Path) -> None:
    cache_directory = tmp_path / "cache"
    graphql = cache_directory / "graphql"
    graphql.mkdir(parents=True)

    result = runner.invoke(
        app,
        ["cache", "clear", "graphql", "--cache-dir", str(cache_directory)],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "cancelled" in result.stdout
    assert graphql.exists()


def test_doctor_reports_local_state_without_requiring_token(tmp_path: Path) -> None:
    from tests.report.test_json import empty_report

    report_path = tmp_path / "report.json"
    report_path.write_text(empty_report().model_dump_json(), encoding="utf-8")
    repositories_file = tmp_path / "repositories"
    repositories_file.write_text("org/private-repo\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "doctor",
            "--report",
            str(report_path),
            "--repos-file",
            str(repositories_file),
            "--cache-dir",
            str(tmp_path / "cache"),
        ],
        env={"GITHUB_TOKEN": ""},
    )

    assert result.exit_code == 0
    assert "GitScope doctor" in result.stdout
    assert "GitHub token" in result.stdout
    assert "token values and cache payloads are hidden" in result.stdout
    assert "private-repo" not in result.stdout


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
            html_path=tmp_path / "report.html",
            markdown_path=tmp_path / "report.md",
            csv_path=tmp_path / "report.csv",
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
    assert "Contribution summary" in result.stdout
    assert "Authored commits" in result.stdout
    assert "Authored pull requests" in result.stdout
    assert "Authored issues" in result.stdout
    assert "Submitted reviews" in result.stdout
    assert "0 inferred languages" in result.stdout
    assert "0 days with 0 career milestones" in result.stdout
    assert "Wrote 0 interactive charts" in result.stdout
    assert "dashboard" in result.stdout
    assert "report.html" in result.stdout
    assert "Markdown report" in result.stdout
    assert "report.md" in result.stdout
    assert "CSV export" in result.stdout
    assert "report.csv" in result.stdout
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
