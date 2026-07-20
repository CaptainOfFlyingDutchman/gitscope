"""Tests for pull-request review collection."""

from typing import Any

import pytest

from gitscope.github.reviews import ReviewCollector
from gitscope.models.review import ReviewState


def review_node(identifier: int, state: str) -> dict[str, Any]:
    return {
        "id": f"REVIEW_{identifier}",
        "state": state,
        "createdAt": f"2026-01-{identifier:02d}T00:00:00Z",
        "submittedAt": f"2026-01-{identifier:02d}T01:00:00Z",
        "url": f"https://github.com/review/{identifier}",
    }


def reviewed_search_page(
    *,
    has_more_reviews: bool,
    issue_count: int = 1,
    nodes: list[dict[str, Any]] | None = None,
) -> dict[str, object]:
    default_nodes = [
        {
            "id": "PR_1",
            "number": 1,
            "title": "Reviewed PR",
            "url": "https://github.com/josys-src/frontend/pull/1",
            "repository": {"nameWithOwner": "josys-src/frontend"},
            "reviews": {
                "nodes": [review_node(1, "APPROVED")],
                "pageInfo": {
                    "hasNextPage": has_more_reviews,
                    "endCursor": "review-next" if has_more_reviews else None,
                },
            },
        }
    ]
    return {
        "search": {
            "issueCount": issue_count,
            "nodes": default_nodes if nodes is None else nodes,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        },
        "rateLimit": {
            "cost": 1,
            "remaining": 4998,
            "resetAt": "2026-07-20T12:00:00Z",
        },
    }


class StubGraphQL:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = responses
        self.variables: list[dict[str, Any]] = []

    async def execute(
        self,
        _query: str,
        variables: dict[str, Any],
        *,
        refresh: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        del refresh
        self.variables.append(variables)
        return self.responses.pop(0), False


@pytest.mark.anyio
async def test_review_collector_collects_nested_review_pages() -> None:
    graphql = StubGraphQL(
        [
            reviewed_search_page(has_more_reviews=True),
            {
                "node": {
                    "reviews": {
                        "nodes": [review_node(2, "CHANGES_REQUESTED")],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                },
                "rateLimit": {
                    "cost": 1,
                    "remaining": 4997,
                    "resetAt": "2026-07-20T12:00:00Z",
                },
            },
        ]
    )

    result = await ReviewCollector(graphql).collect(  # type: ignore[arg-type]
        "josys-src",
        ("frontend",),
        "octocat",
    )

    assert [review.state for review in result.reviews] == [
        ReviewState.APPROVED,
        ReviewState.CHANGES_REQUESTED,
    ]
    assert all(review.repository == "josys-src/frontend" for review in result.reviews)
    assert result.stats.api_requests == 2


@pytest.mark.anyio
async def test_review_collector_partitions_searches_over_github_cap() -> None:
    graphql = StubGraphQL(
        [
            reviewed_search_page(
                has_more_reviews=False,
                issue_count=1001,
                nodes=[],
            ),
            reviewed_search_page(has_more_reviews=False),
            reviewed_search_page(
                has_more_reviews=False,
                issue_count=0,
                nodes=[],
            ),
        ]
    )

    result = await ReviewCollector(graphql).collect(  # type: ignore[arg-type]
        "josys-src",
        ("frontend",),
        "octocat",
    )

    assert len(result.reviews) == 1
    assert len(graphql.variables) == 3
    assert "created:" not in graphql.variables[0]["query"]
    assert "created:" in graphql.variables[1]["query"]
    assert "created:" in graphql.variables[2]["query"]
    assert result.stats.warnings == []
