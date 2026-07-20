"""Tests for secure JSON report output."""

import stat
from datetime import UTC, datetime
from pathlib import Path

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
from gitscope.report.json import write_json_report


def empty_report() -> CareerReport:
    return CareerReport(
        organization="josys-src",
        identity=ReportIdentity(username="octocat", authenticated_as="octocat"),
        collection=CollectionMetadata(
            generated_at=datetime(2026, 7, 20, tzinfo=UTC),
            repository_scope_file=".gitscope-repositories",
            repository_count=0,
            github_api_requests=1,
            github_cache_hits=0,
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


def test_json_report_round_trips_with_private_permissions(tmp_path: Path) -> None:
    output_directory = tmp_path / "career-report"

    path = write_json_report(empty_report(), output_directory)
    restored = CareerReport.model_validate_json(path.read_text(encoding="utf-8"))

    assert restored.schema_version == "1.5"
    assert restored.organization == "josys-src"
    assert stat.S_IMODE(output_directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_schema_13_report_remains_readable() -> None:
    payload = empty_report().model_dump(mode="json")
    payload["schema_version"] = "1.3"
    summary = payload["pull_request_summary"]
    payload.pop("issue_summary")
    payload.pop("issues")
    for field in (
        "average_merge_time_hours",
        "median_merge_time_hours",
        "by_repository",
        "largest_by_changes",
        "largest_by_files",
        "longest_running",
        "oldest_open",
    ):
        summary.pop(field)

    restored = CareerReport.model_validate(payload)

    assert restored.schema_version == "1.3"
    assert restored.pull_request_summary.average_merge_time_hours is None
    assert restored.pull_request_summary.longest_running == ()
