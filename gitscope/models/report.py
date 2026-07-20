"""Versioned JSON report contract."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from gitscope.models.commit import CommitContribution
from gitscope.models.pull_request import PullRequest
from gitscope.models.repository import RepositoryVisibility
from gitscope.models.review import PullRequestReview


class ReportModel(BaseModel):
    """Immutable base for report-domain models."""

    model_config = ConfigDict(frozen=True)


class ReportIdentity(ReportModel):
    """Target and authenticated GitHub identities."""

    username: str
    authenticated_as: str


class ReportRepository(ReportModel):
    """Repository metadata safe for the report contract."""

    name_with_owner: str
    url: str
    visibility: RepositoryVisibility
    is_archived: bool
    is_fork: bool
    default_branch: str | None = None
    primary_language: str | None = None
    stars: int
    forks: int


class PullRequestSummary(ReportModel):
    """Aggregate pull-request metrics."""

    total: int
    open: int
    closed: int
    merged: int
    drafts: int
    merge_rate: float | None


class ReviewSummary(ReportModel):
    """Aggregate review metrics."""

    total: int
    approvals: int
    changes_requested: int
    comments: int
    dismissed: int


class CommitSummary(ReportModel):
    """Aggregate authored-commit and code-change metrics."""

    total: int
    additions: int
    deletions: int
    files_changed: int
    merge_commits: int
    first_contribution: datetime | None
    last_contribution: datetime | None
    by_repository: dict[str, int]
    by_year: dict[str, int]
    by_month: dict[str, int]
    by_weekday: dict[str, int]
    by_hour: dict[str, int]


class RepositoryContributionSummary(ReportModel):
    """Target-user activity and code changes within one repository."""

    name_with_owner: str
    primary_language: str | None
    is_archived: bool
    commits: int
    pull_requests: int
    reviews: int
    additions: int
    deletions: int
    files_changed: int
    first_contribution: datetime | None
    last_contribution: datetime | None


class CodeChangeBreakdown(ReportModel):
    """Cumulative contributed changes grouped by a safe categorical label."""

    name: str
    additions: int
    deletions: int
    files_changed: int


class LanguageSummary(ReportModel):
    """Repository metadata languages and contribution-based file analytics."""

    primary_repository_languages: dict[str, int]
    contributed_languages: tuple[CodeChangeBreakdown, ...]
    file_extensions: tuple[CodeChangeBreakdown, ...]


class ActivityPeriod(ReportModel):
    """Commit, pull-request, and review counts for a month or year."""

    period: str
    commits: int
    pull_requests: int
    reviews: int
    total: int


class CareerMilestone(ReportModel):
    """A deterministic event in the target user's contribution history."""

    key: str
    label: str
    activity_type: Literal["commit", "pull_request", "review", "contribution"]
    occurred_at: datetime
    repository: str
    sequence: int | None = None


class TimelineSummary(ReportModel):
    """Unified contribution history ready for reports and charts."""

    first_contribution: datetime | None
    last_contribution: datetime | None
    career_span_days: int
    active_days: int
    monthly_activity: tuple[ActivityPeriod, ...]
    yearly_activity: tuple[ActivityPeriod, ...]
    most_active_month: ActivityPeriod | None
    most_active_year: ActivityPeriod | None
    milestones: tuple[CareerMilestone, ...]


class CollectionMetadata(ReportModel):
    """Provenance and completeness information for a report run."""

    generated_at: datetime
    repository_scope_file: str
    repository_count: int
    github_api_requests: int
    github_cache_hits: int
    git_repositories_processed: int = 0
    git_repositories_failed: int = 0
    graphql_rate_limit_remaining: int | None = None
    graphql_rate_limit_reset_at: datetime | None = None
    warnings: tuple[str, ...] = ()


class CareerReport(ReportModel):
    """Stable, versioned JSON representation of collected GitScope data."""

    schema_version: Literal["1.3"] = "1.3"
    organization: str
    identity: ReportIdentity
    collection: CollectionMetadata
    repositories: tuple[ReportRepository, ...]
    commit_summary: CommitSummary
    repository_analytics: tuple[RepositoryContributionSummary, ...]
    language_summary: LanguageSummary
    timeline: TimelineSummary
    pull_request_summary: PullRequestSummary
    review_summary: ReviewSummary
    pull_requests: tuple[PullRequest, ...]
    reviews: tuple[PullRequestReview, ...]
    commits: tuple[CommitContribution, ...]
