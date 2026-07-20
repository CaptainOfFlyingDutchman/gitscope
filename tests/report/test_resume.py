"""Tests for structured résumé portfolio generation."""

import stat
from datetime import UTC, datetime
from pathlib import Path

from gitscope.models.report import (
    ActivityPeriod,
    CareerMilestone,
    CareerReport,
    CodeChangeBreakdown,
    CommitSummary,
    IssueSummary,
    LanguageSummary,
    PullRequestSummary,
    ReviewSummary,
    TimelineSummary,
)
from gitscope.models.resume import ResumeProfile
from gitscope.report.resume import build_resume_document, generate_resume_portfolio
from tests.report.test_json import empty_report


def contribution_report() -> CareerReport:
    timestamp = datetime(2024, 1, 10, tzinfo=UTC)
    period = ActivityPeriod(
        period="2024",
        commits=500,
        pull_requests=40,
        reviews=1000,
        total=1540,
    )
    return empty_report().model_copy(
        update={
            "organization": "example-org",
            "collection": empty_report().collection.model_copy(update={"repository_count": 7}),
            "commit_summary": CommitSummary(
                total=500,
                additions=1000,
                deletions=200,
                files_changed=90,
                merge_commits=10,
                first_contribution=timestamp,
                last_contribution=timestamp,
                by_repository={"example-org/private-repo": 500},
                by_year={"2024": 500},
                by_month={"2024-01": 500},
                by_weekday={"Wednesday": 500},
                by_hour={"10": 500},
            ),
            "pull_request_summary": PullRequestSummary(
                total=40,
                open=4,
                closed=6,
                merged=30,
                drafts=1,
                merge_rate=30 / 36,
            ),
            "review_summary": ReviewSummary(
                total=1000,
                approvals=700,
                changes_requested=100,
                comments=190,
                dismissed=10,
            ),
            "issue_summary": IssueSummary(
                total=8,
                open=2,
                closed=6,
                closure_rate=0.75,
                total_comments=12,
            ),
            "language_summary": LanguageSummary(
                primary_repository_languages={"TypeScript": 4},
                contributed_languages=(
                    CodeChangeBreakdown(
                        name="Dependency Lockfile",
                        additions=1000,
                        deletions=200,
                        files_changed=10,
                    ),
                    CodeChangeBreakdown(
                        name="TypeScript", additions=800, deletions=100, files_changed=70
                    ),
                    CodeChangeBreakdown(
                        name="Python", additions=200, deletions=100, files_changed=20
                    ),
                ),
                file_extensions=(),
            ),
            "timeline": TimelineSummary(
                first_contribution=timestamp,
                last_contribution=timestamp,
                career_span_days=365,
                active_days=120,
                monthly_activity=(),
                yearly_activity=(period,),
                most_active_month=None,
                most_active_year=period,
                milestones=(
                    CareerMilestone(
                        key="commit_500",
                        label="500th commit",
                        activity_type="commit",
                        occurred_at=timestamp,
                        repository="example-org/private-repo",
                        sequence=500,
                    ),
                ),
            ),
        }
    )


def test_resume_document_uses_evidence_without_repository_names() -> None:
    report = contribution_report()
    profile = ResumeProfile(
        name="Manvendra Singh",
        title="Staff Engineer",
        company="Josys",
        website="https://www.manvendrask.com/about",
    )

    document = build_resume_document(report, profile)
    rendered = " ".join((document.summary, document.linkedin_summary, *document.highlights))

    assert document.profile.title == "Staff Engineer"
    assert document.technologies == ("TypeScript", "Python")
    assert len(document.metrics) == 5
    assert document.milestones[0].label == "500th commit"
    assert "500 authored commits" in rendered
    assert "1,000 submitted code reviews" in rendered
    assert "8 authored issues" in rendered
    assert "private-repo" not in rendered


def test_generate_resume_portfolio_writes_private_synchronized_outputs(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(contribution_report().model_dump_json(), encoding="utf-8")
    output_directory = tmp_path / "portfolio"

    generated = generate_resume_portfolio(
        report_path,
        output_directory,
        name="Manvendra <Singh>",
        title="Staff Engineer",
        company="Josys",
        website="https://www.manvendrask.com/about",
    )
    markdown = generated.markdown_path.read_text(encoding="utf-8")
    html = generated.html_path.read_text(encoding="utf-8")

    assert generated.markdown_path == output_directory / "resume.md"
    assert generated.html_path == output_directory / "resume.html"
    assert stat.S_IMODE(output_directory.stat().st_mode) == 0o700
    for path in (
        generated.markdown_path,
        generated.html_path,
        output_directory / "resume.css",
        output_directory / "resume.js",
        output_directory / "favicon.svg",
    ):
        assert path.exists()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert "Manvendra &lt;Singh&gt;" in markdown
    assert "Manvendra &lt;Singh&gt;" in html
    assert "private-repo" not in markdown
    assert "private-repo" not in html
    assert 'id="resume-theme-toggle"' in html
    assert 'id="resume-print"' in html
    assert '<link rel="icon" href="favicon.svg" type="image/svg+xml">' in html
    assert 'href="https://www.manvendrask.com/about"' in html
    assert "Made with care and" in markdown
    assert "[**Manvendra Singh**](https://www.manvendrask.com/about)" in markdown
    assert "Made with care and" in html
    assert ">Manvendra Singh</a>" in html
