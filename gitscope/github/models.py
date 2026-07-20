"""Typed models shared by GitHub collectors."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class GitHubModel(BaseModel):
    """Base model accepting GitHub's camelCase field names."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class AuthenticatedUser(GitHubModel):
    """Identity associated with the configured token."""

    login: str
    database_id: int = Field(alias="id")
    name: str | None = None
    avatar_url: str | None = None


class RepositoryVisibility(StrEnum):
    """Visibility values returned by GitHub."""

    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    INTERNAL = "INTERNAL"


class RepositorySummary(GitHubModel):
    """Repository metadata needed by downstream collectors and reports."""

    node_id: str
    name: str
    name_with_owner: str
    url: str
    visibility: RepositoryVisibility
    is_private: bool
    is_archived: bool
    is_fork: bool
    default_branch: str | None = None
    primary_language: str | None = None
    stars: int = 0
    forks: int = 0
    disk_usage_kib: int | None = None
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime | None = None


class RateLimit(GitHubModel):
    """GraphQL rate-limit status after a query."""

    cost: int
    remaining: int
    reset_at: datetime = Field(alias="resetAt")


class RepositoryDiscovery(GitHubModel):
    """Result of discovering repositories visible to the token."""

    repositories: tuple[RepositorySummary, ...]
    source: str
    rate_limit: RateLimit | None = None
    from_cache: bool = False
