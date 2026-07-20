"""Local Git commit contribution models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CommitContribution(BaseModel):
    """A commit authored by the target identity, excluding private identity data."""

    model_config = ConfigDict(frozen=True)

    sha: str
    repository: str
    authored_at: datetime
    additions: int
    deletions: int
    files_changed: int
    is_merge: bool
