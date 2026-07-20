"""Pull-request analytics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from statistics import fmean, median

from gitscope.models.pull_request import PullRequest, PullRequestState
from gitscope.models.report import PullRequestInsight, PullRequestSummary


def summarize_pull_requests(
    pull_requests: Iterable[PullRequest],
    *,
    as_of: datetime | None = None,
) -> PullRequestSummary:
    """Calculate lifecycle totals without treating them as productivity scores."""
    items = tuple(pull_requests)
    merged = sum(item.state is PullRequestState.MERGED for item in items)
    closed = sum(item.state is PullRequestState.CLOSED for item in items)
    completed = merged + closed
    merge_times = [
        _duration_hours(item.created_at, item.merged_at)
        for item in items
        if item.merged_at is not None
    ]
    insights = tuple(_insight(item, as_of=as_of) for item in items)
    largest_by_changes = sorted(
        insights,
        key=lambda item: (
            -(item.additions + item.deletions),
            -item.changed_files,
            item.repository.casefold(),
            item.number,
        ),
    )
    largest_by_files = sorted(
        insights,
        key=lambda item: (
            -item.changed_files,
            -(item.additions + item.deletions),
            item.repository.casefold(),
            item.number,
        ),
    )
    longest_running = sorted(
        insights,
        key=lambda item: (
            -item.duration_hours,
            item.repository.casefold(),
            item.number,
        ),
    )
    oldest_open = [item for item in longest_running if item.state is PullRequestState.OPEN]
    return PullRequestSummary(
        total=len(items),
        open=sum(item.state is PullRequestState.OPEN for item in items),
        closed=closed,
        merged=merged,
        drafts=sum(item.is_draft for item in items),
        merge_rate=round(merged / completed, 4) if completed else None,
        average_merge_time_hours=(round(fmean(merge_times), 2) if merge_times else None),
        median_merge_time_hours=(round(median(merge_times), 2) if merge_times else None),
        by_repository=dict(sorted(Counter(item.repository for item in items).items())),
        largest_by_changes=tuple(largest_by_changes[:10]),
        largest_by_files=tuple(largest_by_files[:10]),
        longest_running=tuple(longest_running[:10]),
        oldest_open=tuple(oldest_open[:10]),
    )


def _insight(item: PullRequest, *, as_of: datetime | None) -> PullRequestInsight:
    completed_at: datetime | None
    if item.state is PullRequestState.MERGED:
        completed_at = item.merged_at or item.closed_at or item.updated_at
    elif item.state is PullRequestState.CLOSED:
        completed_at = item.closed_at or item.updated_at
    else:
        completed_at = None

    endpoint = completed_at or as_of or item.updated_at
    return PullRequestInsight(
        repository=item.repository,
        number=item.number,
        title=item.title,
        url=item.url,
        state=item.state,
        is_draft=item.is_draft,
        created_at=item.created_at,
        completed_at=completed_at,
        duration_hours=_duration_hours(item.created_at, endpoint),
        additions=item.additions,
        deletions=item.deletions,
        changed_files=item.changed_files,
        commit_count=item.commit_count,
    )


def _duration_hours(start: datetime, end: datetime) -> float:
    return round(max(0.0, (end - start).total_seconds() / 3600), 2)
