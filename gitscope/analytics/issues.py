"""Authored-issue analytics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from statistics import fmean, median

from gitscope.models.issue import Issue, IssueState
from gitscope.models.report import IssueSummary


def summarize_issues(issues: Iterable[Issue]) -> IssueSummary:
    """Calculate issue lifecycle totals without treating them as productivity scores."""
    items = tuple(issues)
    closed = sum(item.state is IssueState.CLOSED for item in items)
    close_times = [
        max(0.0, (item.closed_at - item.created_at).total_seconds() / 3600)
        for item in items
        if item.closed_at is not None
    ]
    return IssueSummary(
        total=len(items),
        open=sum(item.state is IssueState.OPEN for item in items),
        closed=closed,
        closure_rate=round(closed / len(items), 4) if items else None,
        average_close_time_hours=(round(fmean(close_times), 2) if close_times else None),
        median_close_time_hours=(round(median(close_times), 2) if close_times else None),
        total_comments=sum(item.comment_count for item in items),
        by_repository=dict(sorted(Counter(item.repository for item in items).items())),
    )
