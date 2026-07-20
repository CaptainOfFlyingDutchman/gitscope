"""Pull-request review domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ReviewState(StrEnum):
    """State of a submitted pull-request review."""

    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMMENTED = "COMMENTED"
    DISMISSED = "DISMISSED"
    PENDING = "PENDING"


class PullRequestReview(BaseModel):
    """Normalized review submitted by the target user."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    repository: str
    pull_request_number: int
    pull_request_title: str
    pull_request_url: str
    state: ReviewState
    created_at: datetime
    submitted_at: datetime | None = None
    url: str
