"""Tests for contribution summaries."""

from datetime import UTC, datetime

from gitscope.analytics.prs import summarize_pull_requests
from gitscope.analytics.reviews import summarize_reviews
from gitscope.models.pull_request import PullRequest, PullRequestState
from gitscope.models.review import PullRequestReview, ReviewState


def pull_request(state: PullRequestState) -> PullRequest:
    return PullRequest(
        node_id=f"PR_{state}",
        repository="josys-src/frontend",
        number=1,
        title="PR",
        url="https://github.com/pr/1",
        state=state,
        is_draft=False,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
        additions=1,
        deletions=1,
        changed_files=1,
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
    summary = summarize_pull_requests(
        [pull_request(PullRequestState.MERGED), pull_request(PullRequestState.CLOSED)]
    )

    assert summary.total == 2
    assert summary.merged == 1
    assert summary.merge_rate == 0.5


def test_review_summary() -> None:
    summary = summarize_reviews(
        [review(ReviewState.APPROVED), review(ReviewState.CHANGES_REQUESTED)]
    )

    assert summary.total == 2
    assert summary.approvals == 1
    assert summary.changes_requested == 1
