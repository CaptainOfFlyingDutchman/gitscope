"""Tests for reusable GitScope chart figures."""

from datetime import UTC, datetime

from gitscope.charts.activity import (
    monthly_activity_chart,
    pull_request_states_chart,
    yearly_activity_chart,
)
from gitscope.charts.commits import commit_patterns_chart
from gitscope.charts.languages import contributed_languages_chart, file_extensions_chart
from gitscope.charts.repositories import repository_rankings_chart
from gitscope.charts.reviews import review_activity_chart, review_states_chart
from gitscope.charts.timeline import career_milestones_chart
from gitscope.models.report import (
    ActivityPeriod,
    CareerMilestone,
    CodeChangeBreakdown,
    CommitSummary,
    LanguageSummary,
    PullRequestSummary,
    RepositoryContributionSummary,
    ReviewSummary,
    TimelineSummary,
)


def test_chart_builders_preserve_report_values() -> None:
    occurred_at = datetime(2026, 1, 1, tzinfo=UTC)
    monthly = ActivityPeriod(
        period="2026-01",
        commits=12,
        pull_requests=3,
        reviews=7,
        total=22,
    )
    timeline = TimelineSummary(
        first_contribution=occurred_at,
        last_contribution=occurred_at,
        career_span_days=0,
        active_days=1,
        monthly_activity=(monthly,),
        yearly_activity=(monthly.model_copy(update={"period": "2026"}),),
        most_active_month=monthly,
        most_active_year=monthly.model_copy(update={"period": "2026"}),
        milestones=(
            CareerMilestone(
                key="first_commit",
                label="First authored commit",
                activity_type="commit",
                occurred_at=occurred_at,
                repository="org/repo",
                sequence=1,
            ),
        ),
    )
    commit_summary = CommitSummary(
        total=12,
        additions=100,
        deletions=20,
        files_changed=8,
        merge_commits=1,
        first_contribution=occurred_at,
        last_contribution=occurred_at,
        by_repository={"org/repo": 12},
        by_year={"2026": 12},
        by_month={"2026-01": 12},
        by_weekday={"Thursday": 12},
        by_hour={"10": 12},
    )
    repository = RepositoryContributionSummary(
        name_with_owner="org/repo",
        primary_language="TypeScript",
        is_archived=False,
        commits=12,
        pull_requests=3,
        reviews=7,
        additions=100,
        deletions=20,
        files_changed=8,
        first_contribution=occurred_at,
        last_contribution=occurred_at,
    )
    pull_requests = PullRequestSummary(
        total=3,
        open=1,
        closed=0,
        merged=2,
        drafts=1,
        merge_rate=1.0,
    )
    reviews = ReviewSummary(
        total=7,
        approvals=4,
        changes_requested=1,
        comments=1,
        dismissed=1,
    )
    languages = LanguageSummary(
        primary_repository_languages={"TypeScript": 1},
        contributed_languages=(
            CodeChangeBreakdown(name="TypeScript", additions=100, deletions=20, files_changed=8),
        ),
        file_extensions=(
            CodeChangeBreakdown(name=".ts", additions=100, deletions=20, files_changed=8),
        ),
    )

    monthly_figure = monthly_activity_chart(timeline)
    yearly_figure = yearly_activity_chart(timeline)
    commit_figure = commit_patterns_chart(commit_summary)
    repository_figure = repository_rankings_chart((repository,))
    pull_request_figure = pull_request_states_chart(pull_requests)
    review_activity_figure = review_activity_chart(timeline)
    review_state_figure = review_states_chart(reviews)
    language_figure = contributed_languages_chart(languages)
    extension_figure = file_extensions_chart(languages)
    milestone_figure = career_milestones_chart(timeline)

    assert list(monthly_figure.data[0].y) == [12]
    assert len(yearly_figure.data) == 3
    assert len(commit_figure.data) == 2
    assert len(repository_figure.data) == 3
    assert list(pull_request_figure.data[0].x) == [2, 1, 0]
    assert list(review_activity_figure.data[0].y) == [7]
    assert sum(review_state_figure.data[0].x) == 7
    assert len(language_figure.data) == 2
    assert list(extension_figure.data[0].x) == [8]
    assert list(milestone_figure.data[0].text) == ["First authored commit"]
