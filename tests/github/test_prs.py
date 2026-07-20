"""Tests for authored pull-request collection."""

from typing import Any

import pytest

from gitscope.github.prs import PullRequestCollector
from gitscope.models.pull_request import PullRequestState


def pull_request_node(number: int, *, state: str = "MERGED") -> dict[str, Any]:
    return {
        "id": f"PR_{number}",
        "number": number,
        "title": f"Pull request {number}",
        "url": f"https://github.com/josys-src/frontend/pull/{number}",
        "state": state,
        "isDraft": False,
        "createdAt": f"2026-01-{number:02d}T00:00:00Z",
        "updatedAt": f"2026-02-{number:02d}T00:00:00Z",
        "closedAt": f"2026-02-{number:02d}T00:00:00Z",
        "mergedAt": f"2026-02-{number:02d}T00:00:00Z" if state == "MERGED" else None,
        "additions": 100,
        "deletions": 20,
        "changedFiles": 5,
        "commits": {"totalCount": 3},
        "repository": {"nameWithOwner": "josys-src/frontend"},
    }


def pull_request_page(
    nodes: list[dict[str, Any]],
    *,
    has_next_page: bool,
    cursor: str | None,
    issue_count: int,
) -> dict[str, object]:
    return {
        "search": {
            "issueCount": issue_count,
            "nodes": nodes,
            "pageInfo": {"hasNextPage": has_next_page, "endCursor": cursor},
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
async def test_pull_request_collector_paginates_and_normalizes() -> None:
    graphql = StubGraphQL(
        [
            pull_request_page(
                [pull_request_node(1)],
                has_next_page=True,
                cursor="next",
                issue_count=2,
            ),
            pull_request_page(
                [pull_request_node(2, state="CLOSED")],
                has_next_page=False,
                cursor=None,
                issue_count=2,
            ),
        ]
    )

    result = await PullRequestCollector(graphql).collect(  # type: ignore[arg-type]
        "josys-src",
        ("frontend",),
        "octocat",
    )

    assert [item.number for item in result.pull_requests] == [1, 2]
    assert result.pull_requests[0].state is PullRequestState.MERGED
    assert result.pull_requests[0].commit_count == 3
    assert [variables["cursor"] for variables in graphql.variables] == [None, "next"]
    assert result.stats.api_requests == 2


@pytest.mark.anyio
async def test_pull_request_collector_warns_about_truncated_search() -> None:
    graphql = StubGraphQL(
        [
            pull_request_page(
                [pull_request_node(1)],
                has_next_page=False,
                cursor=None,
                issue_count=2,
            )
        ]
    )

    result = await PullRequestCollector(graphql).collect(  # type: ignore[arg-type]
        "josys-src",
        ("frontend",),
        "octocat",
    )

    assert len(result.stats.warnings) == 1
    assert "returned 1 of 2" in result.stats.warnings[0]
