"""Pull-request domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class PullRequestState(StrEnum):
    """Lifecycle state of a GitHub pull request."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    MERGED = "MERGED"


class PullRequest(BaseModel):
    """Normalized authored pull request independent of GitHub transport details."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    repository: str
    number: int
    title: str
    url: str
    state: PullRequestState
    is_draft: bool
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    merged_at: datetime | None = None
    additions: int
    deletions: int
    changed_files: int
    commit_count: int
