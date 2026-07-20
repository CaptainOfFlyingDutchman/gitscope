"""Tests for contribution summaries."""

from datetime import UTC, datetime, timedelta

from gitscope.analytics.prs import summarize_pull_requests
from gitscope.analytics.reviews import summarize_reviews
from gitscope.models.pull_request import PullRequest, PullRequestState
from gitscope.models.review import PullRequestReview, ReviewState


def pull_request(
    state: PullRequestState,
    *,
    number: int = 1,
    repository: str = "josys-src/frontend",
    duration_days: int = 1,
    additions: int = 1,
    changed_files: int = 1,
) -> PullRequest:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    completed_at = created_at + timedelta(days=duration_days)
    return PullRequest(
        node_id=f"PR_{state}_{number}",
        repository=repository,
        number=number,
        title="PR",
        url="https://github.com/pr/1",
        state=state,
        is_draft=False,
        created_at=created_at,
        updated_at=completed_at,
        closed_at=completed_at if state is PullRequestState.CLOSED else None,
        merged_at=completed_at if state is PullRequestState.MERGED else None,
        additions=additions,
        deletions=1,
        changed_files=changed_files,
        commit_count=1,
    )


def review(state: ReviewState) -> PullRequestReview:
    return PullRequestReview(
        node_id=f"REVIEW_{state}",
        repository="josys-src/frontend",
        pull_request_number=1,
        pull_request_title="PR",
        pull_request_url="https://github.com/pr/1",
        state=state,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
        url="https://github.com/review/1",
    )


def test_pull_request_summary() -> None:
    as_of = datetime(2026, 1, 11, tzinfo=UTC)
    summary = summarize_pull_requests(
        [
            pull_request(
                PullRequestState.MERGED,
                number=1,
                duration_days=2,
                additions=20,
                changed_files=3,
            ),
            pull_request(
                PullRequestState.MERGED,
                number=2,
                duration_days=4,
                repository="josys-src/backend",
            ),
            pull_request(PullRequestState.CLOSED, number=3, duration_days=5),
            pull_request(PullRequestState.OPEN, number=4),
        ],
        as_of=as_of,
    )

    assert summary.total == 4
    assert summary.merged == 2
    assert summary.merge_rate == 0.6667
    assert summary.average_merge_time_hours == 72
    assert summary.median_merge_time_hours == 72
    assert summary.by_repository == {
        "josys-src/backend": 1,
        "josys-src/frontend": 3,
    }
    assert summary.largest_by_changes[0].number == 1
    assert summary.largest_by_files[0].number == 1
    assert summary.longest_running[0].number == 4
    assert summary.longest_running[0].duration_hours == 240
    assert summary.oldest_open[0].number == 4


def test_review_summary() -> None:
    summary = summarize_reviews(
        [review(ReviewState.APPROVED), review(ReviewState.CHANGES_REQUESTED)]
    )

    assert summary.total == 2
    assert summary.approvals == 1
    assert summary.changes_requested == 1
