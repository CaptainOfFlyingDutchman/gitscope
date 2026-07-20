"""Versioned JSON report contract."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

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


class CollectionMetadata(ReportModel):
    """Provenance and completeness information for a report run."""

    generated_at: datetime
    repository_scope_file: str
    repository_count: int
    github_api_requests: int
    github_cache_hits: int
    graphql_rate_limit_remaining: int | None = None
    graphql_rate_limit_reset_at: datetime | None = None
    warnings: tuple[str, ...] = ()


class CareerReport(ReportModel):
    """Stable, versioned JSON representation of collected GitScope data."""

    schema_version: Literal["1.0"] = "1.0"
    organization: str
    identity: ReportIdentity
    collection: CollectionMetadata
    repositories: tuple[ReportRepository, ...]
    pull_request_summary: PullRequestSummary
    review_summary: ReviewSummary
    pull_requests: tuple[PullRequest, ...]
    reviews: tuple[PullRequestReview, ...]
