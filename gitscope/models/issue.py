"""Issue contribution domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class IssueState(StrEnum):
    """Lifecycle state of a GitHub issue."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


class Issue(BaseModel):
    """Normalized authored issue independent of GitHub transport details."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    repository: str
    number: int
    title: str
    url: str
    state: IssueState
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    comment_count: int
    labels: tuple[str, ...] = ()
