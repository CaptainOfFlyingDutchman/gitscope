"""Unified contribution timeline and career milestone analytics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from gitscope.models.commit import CommitContribution
from gitscope.models.issue import Issue
from gitscope.models.pull_request import PullRequest
from gitscope.models.report import ActivityPeriod, CareerMilestone, TimelineSummary
from gitscope.models.review import PullRequestReview

ActivityType = Literal["commit", "pull_request", "review", "issue"]


@dataclass(frozen=True, slots=True)
class _ActivityEvent:
    occurred_at: datetime
    activity_type: ActivityType
    repository: str
    stable_id: str


def build_timeline(
    commits: tuple[CommitContribution, ...],
    pull_requests: tuple[PullRequest, ...],
    reviews: tuple[PullRequestReview, ...],
    issues: tuple[Issue, ...] = (),
) -> TimelineSummary:
    """Create UTC-normalized activity periods and deterministic career milestones."""
    events = _events(commits, pull_requests, reviews, issues)
    if not events:
        return TimelineSummary(
            first_contribution=None,
            last_contribution=None,
            career_span_days=0,
            active_days=0,
            monthly_activity=(),
            yearly_activity=(),
            most_active_month=None,
            most_active_year=None,
            milestones=(),
        )

    monthly_activity = _monthly_activity(events)
    yearly_activity = _yearly_activity(events)
    first = events[0]
    last = events[-1]
    return TimelineSummary(
        first_contribution=first.occurred_at,
        last_contribution=last.occurred_at,
        career_span_days=(last.occurred_at.date() - first.occurred_at.date()).days,
        active_days=len({event.occurred_at.date() for event in events}),
        monthly_activity=monthly_activity,
        yearly_activity=yearly_activity,
        most_active_month=max(monthly_activity, key=lambda period: period.total),
        most_active_year=max(yearly_activity, key=lambda period: period.total),
        milestones=_milestones(events, commits, pull_requests, reviews, issues),
    )


def _events(
    commits: tuple[CommitContribution, ...],
    pull_requests: tuple[PullRequest, ...],
    reviews: tuple[PullRequestReview, ...],
    issues: tuple[Issue, ...],
) -> tuple[_ActivityEvent, ...]:
    events = [
        _ActivityEvent(_utc(commit.authored_at), "commit", commit.repository, commit.sha)
        for commit in commits
    ]
    events.extend(
        _ActivityEvent(
            _utc(pull_request.created_at),
            "pull_request",
            pull_request.repository,
            pull_request.node_id,
        )
        for pull_request in pull_requests
    )
    events.extend(
        _ActivityEvent(
            _utc(review.submitted_at or review.created_at),
            "review",
            review.repository,
            review.node_id,
        )
        for review in reviews
    )
    events.extend(
        _ActivityEvent(_utc(issue.created_at), "issue", issue.repository, issue.node_id)
        for issue in issues
    )
    return tuple(
        sorted(
            events,
            key=lambda event: (
                event.occurred_at,
                event.activity_type,
                event.repository,
                event.stable_id,
            ),
        )
    )


def _monthly_activity(events: tuple[_ActivityEvent, ...]) -> tuple[ActivityPeriod, ...]:
    totals = _period_totals(events, period_format="%Y-%m")
    first = events[0].occurred_at
    last = events[-1].occurred_at
    periods: list[ActivityPeriod] = []
    year, month = first.year, first.month
    while (year, month) <= (last.year, last.month):
        period = f"{year:04d}-{month:02d}"
        periods.append(_activity_period(period, totals[period]))
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return tuple(periods)


def _yearly_activity(events: tuple[_ActivityEvent, ...]) -> tuple[ActivityPeriod, ...]:
    totals = _period_totals(events, period_format="%Y")
    return tuple(
        _activity_period(str(year), totals[str(year)])
        for year in range(events[0].occurred_at.year, events[-1].occurred_at.year + 1)
    )


def _period_totals(
    events: tuple[_ActivityEvent, ...],
    *,
    period_format: str,
) -> defaultdict[str, dict[ActivityType, int]]:
    totals: defaultdict[str, dict[ActivityType, int]] = defaultdict(
        lambda: {"commit": 0, "pull_request": 0, "review": 0, "issue": 0}
    )
    for event in events:
        totals[event.occurred_at.strftime(period_format)][event.activity_type] += 1
    return totals


def _activity_period(period: str, totals: dict[ActivityType, int]) -> ActivityPeriod:
    commits = totals["commit"]
    pull_requests = totals["pull_request"]
    reviews = totals["review"]
    issues = totals["issue"]
    return ActivityPeriod(
        period=period,
        commits=commits,
        pull_requests=pull_requests,
        reviews=reviews,
        total=commits + pull_requests + reviews + issues,
        issues=issues,
    )


def _milestones(
    events: tuple[_ActivityEvent, ...],
    commits: tuple[CommitContribution, ...],
    pull_requests: tuple[PullRequest, ...],
    reviews: tuple[PullRequestReview, ...],
    issues: tuple[Issue, ...],
) -> tuple[CareerMilestone, ...]:
    ordered_commits = sorted(commits, key=lambda item: (_utc(item.authored_at), item.sha))
    ordered_pull_requests = sorted(
        pull_requests,
        key=lambda item: (_utc(item.created_at), item.repository, item.number),
    )
    ordered_reviews = sorted(
        reviews,
        key=lambda item: (
            _utc(item.submitted_at or item.created_at),
            item.repository,
            item.node_id,
        ),
    )
    ordered_issues = sorted(
        issues,
        key=lambda item: (_utc(item.created_at), item.repository, item.number),
    )
    milestones = [
        CareerMilestone(
            key="first_contribution",
            label="First recorded contribution",
            activity_type="contribution",
            occurred_at=events[0].occurred_at,
            repository=events[0].repository,
        )
    ]
    if ordered_commits:
        first_commit = ordered_commits[0]
        milestones.append(
            CareerMilestone(
                key="first_commit",
                label="First authored commit",
                activity_type="commit",
                occurred_at=_utc(first_commit.authored_at),
                repository=first_commit.repository,
                sequence=1,
            )
        )
    _append_sequence_milestones(
        milestones,
        ordered_commits,
        thresholds=(100, 500, 1000),
        activity_type="commit",
    )

    merged_pull_requests = sorted(
        (item for item in pull_requests if item.merged_at is not None),
        key=lambda item: (
            _utc(item.merged_at or item.created_at),
            item.repository,
            item.number,
        ),
    )
    if merged_pull_requests:
        first_merged = merged_pull_requests[0]
        assert first_merged.merged_at is not None
        milestones.append(
            CareerMilestone(
                key="first_merged_pull_request",
                label="First merged pull request",
                activity_type="pull_request",
                occurred_at=_utc(first_merged.merged_at),
                repository=first_merged.repository,
            )
        )
    _append_sequence_milestones(
        milestones,
        ordered_pull_requests,
        thresholds=(100,),
        activity_type="pull_request",
    )
    _append_sequence_milestones(
        milestones,
        ordered_reviews,
        thresholds=(100, 500, 1000, 2500),
        activity_type="review",
    )
    if ordered_issues:
        first_issue = ordered_issues[0]
        milestones.append(
            CareerMilestone(
                key="first_issue",
                label="First authored issue",
                activity_type="issue",
                occurred_at=_utc(first_issue.created_at),
                repository=first_issue.repository,
                sequence=1,
            )
        )
    _append_sequence_milestones(
        milestones,
        ordered_issues,
        thresholds=(100,),
        activity_type="issue",
    )
    milestones.append(
        CareerMilestone(
            key="last_contribution",
            label="Most recent recorded contribution",
            activity_type="contribution",
            occurred_at=events[-1].occurred_at,
            repository=events[-1].repository,
        )
    )
    return tuple(sorted(milestones, key=lambda item: item.occurred_at))


def _append_sequence_milestones(
    milestones: list[CareerMilestone],
    items: list[CommitContribution] | list[PullRequest] | list[PullRequestReview] | list[Issue],
    *,
    thresholds: tuple[int, ...],
    activity_type: ActivityType,
) -> None:
    for threshold in thresholds:
        if len(items) < threshold:
            continue
        item = items[threshold - 1]
        if isinstance(item, CommitContribution):
            occurred_at = item.authored_at
            repository = item.repository
        elif isinstance(item, (PullRequest, Issue)):
            occurred_at = item.created_at
            repository = item.repository
        else:
            occurred_at = item.submitted_at or item.created_at
            repository = item.repository
        display_type = activity_type.replace("_", " ")
        milestones.append(
            CareerMilestone(
                key=f"{activity_type}_{threshold}",
                label=f"{threshold:,}th {display_type}",
                activity_type=activity_type,
                occurred_at=_utc(occurred_at),
                repository=repository,
                sequence=threshold,
            )
        )


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)
