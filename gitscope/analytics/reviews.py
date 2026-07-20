"""Pull-request review analytics."""

from __future__ import annotations

from collections.abc import Iterable

from gitscope.models.report import ReviewSummary
from gitscope.models.review import PullRequestReview, ReviewState


def summarize_reviews(reviews: Iterable[PullRequestReview]) -> ReviewSummary:
    """Calculate review-state totals."""
    items = tuple(reviews)
    return ReviewSummary(
        total=len(items),
        approvals=sum(item.state is ReviewState.APPROVED for item in items),
        changes_requested=sum(item.state is ReviewState.CHANGES_REQUESTED for item in items),
        comments=sum(item.state is ReviewState.COMMENTED for item in items),
        dismissed=sum(item.state is ReviewState.DISMISSED for item in items),
    )
