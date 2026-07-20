"""Tests for unified activity periods and career milestones."""

from datetime import UTC, datetime, timedelta

from gitscope.analytics.timeline import build_timeline
from gitscope.models.commit import CommitContribution
from gitscope.models.issue import Issue, IssueState
from gitscope.models.pull_request import PullRequest, PullRequestState
from gitscope.models.review import PullRequestReview, ReviewState


def commit(index: int, occurred_at: datetime) -> CommitContribution:
    return CommitContribution(
        sha=f"{index:040x}",
        repository="org/repo",
        authored_at=occurred_at,
        additions=1,
        deletions=0,
        files_changed=1,
        is_merge=False,
    )


def pull_request(index: int, occurred_at: datetime, *, merged: bool = False) -> PullRequest:
    return PullRequest(
        node_id=f"PR_{index}",
        repository="org/repo",
        number=index,
        title=f"PR {index}",
        url=f"https://github.com/org/repo/pull/{index}",
        state=PullRequestState.MERGED if merged else PullRequestState.OPEN,
        is_draft=False,
        created_at=occurred_at,
        updated_at=occurred_at,
        merged_at=occurred_at if merged else None,
        additions=1,
        deletions=0,
        changed_files=1,
        commit_count=1,
    )


def review(index: int, occurred_at: datetime) -> PullRequestReview:
    return PullRequestReview(
        node_id=f"REVIEW_{index}",
        repository="org/repo",
        pull_request_number=index,
        pull_request_title=f"PR {index}",
        pull_request_url=f"https://github.com/org/repo/pull/{index}",
        state=ReviewState.APPROVED,
        created_at=occurred_at,
        submitted_at=occurred_at,
        url=f"https://github.com/org/repo/pull/{index}#review",
    )


def issue(index: int, occurred_at: datetime) -> Issue:
    return Issue(
        node_id=f"ISSUE_{index}",
        repository="org/repo",
        number=index,
        title=f"Issue {index}",
        url=f"https://github.com/org/repo/issues/{index}",
        state=IssueState.OPEN,
        created_at=occurred_at,
        updated_at=occurred_at,
        comment_count=0,
    )


def test_timeline_zero_fills_months_and_combines_activity() -> None:
    january = datetime(2025, 1, 1, tzinfo=UTC)
    march = datetime(2025, 3, 1, tzinfo=UTC)

    timeline = build_timeline(
        (commit(1, january),),
        (pull_request(1, march, merged=True),),
        (review(1, march + timedelta(days=1)),),
        (issue(1, march + timedelta(days=2)),),
    )

    assert [period.period for period in timeline.monthly_activity] == [
        "2025-01",
        "2025-02",
        "2025-03",
    ]
    assert timeline.monthly_activity[1].total == 0
    assert timeline.monthly_activity[2].pull_requests == 1
    assert timeline.monthly_activity[2].reviews == 1
    assert timeline.monthly_activity[2].issues == 1
    assert timeline.yearly_activity[0].total == 4
    assert timeline.most_active_month == timeline.monthly_activity[2]
    assert timeline.active_days == 4
    assert timeline.career_span_days == 61


def test_timeline_emits_reached_sequence_milestones() -> None:
    start = datetime(2022, 1, 1, tzinfo=UTC)
    commits = tuple(commit(index + 1, start + timedelta(minutes=index)) for index in range(1000))
    pull_requests = tuple(
        pull_request(
            index + 1,
            start + timedelta(days=10, minutes=index),
            merged=index == 0,
        )
        for index in range(100)
    )
    reviews = tuple(
        review(index + 1, start + timedelta(days=20, minutes=index)) for index in range(2500)
    )
    issues = tuple(
        issue(index + 1, start + timedelta(days=30, minutes=index)) for index in range(100)
    )

    timeline = build_timeline(commits, pull_requests, reviews, issues)
    keys = {milestone.key for milestone in timeline.milestones}

    assert {
        "first_contribution",
        "first_commit",
        "commit_100",
        "commit_500",
        "commit_1000",
        "first_merged_pull_request",
        "pull_request_100",
        "review_100",
        "review_500",
        "review_1000",
        "review_2500",
        "first_issue",
        "issue_100",
        "last_contribution",
    } == keys
    assert list(timeline.milestones) == sorted(
        timeline.milestones,
        key=lambda milestone: milestone.occurred_at,
    )


def test_empty_timeline() -> None:
    timeline = build_timeline((), (), ())

    assert timeline.first_contribution is None
    assert timeline.career_span_days == 0
    assert timeline.monthly_activity == ()
    assert timeline.milestones == ()
