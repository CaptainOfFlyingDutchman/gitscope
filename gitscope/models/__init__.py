"""API-independent domain models for GitScope reports."""

from gitscope.models.pull_request import PullRequest, PullRequestState
from gitscope.models.report import CareerReport
from gitscope.models.review import PullRequestReview, ReviewState

__all__ = [
    "CareerReport",
    "PullRequest",
    "PullRequestReview",
    "PullRequestState",
    "ReviewState",
]
