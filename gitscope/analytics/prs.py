"""Pull-request analytics."""

from __future__ import annotations

from collections.abc import Iterable

from gitscope.models.pull_request import PullRequest, PullRequestState
from gitscope.models.report import PullRequestSummary


def summarize_pull_requests(pull_requests: Iterable[PullRequest]) -> PullRequestSummary:
    """Calculate lifecycle totals without treating them as productivity scores."""
    items = tuple(pull_requests)
    merged = sum(item.state is PullRequestState.MERGED for item in items)
    closed = sum(item.state is PullRequestState.CLOSED for item in items)
    completed = merged + closed
    return PullRequestSummary(
        total=len(items),
        open=sum(item.state is PullRequestState.OPEN for item in items),
        closed=closed,
        merged=merged,
        drafts=sum(item.is_draft for item in items),
        merge_rate=round(merged / completed, 4) if completed else None,
    )
