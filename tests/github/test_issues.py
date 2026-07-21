"""Tests for authored-issue collection."""

from typing import Any

import pytest

from gitscope.github.errors import RateLimitSafetyError
from gitscope.github.issues import IssueCollector
from gitscope.models.issue import IssueState


def issue_node(number: int, *, state: str = "OPEN") -> dict[str, Any]:
    return {
        "id": f"ISSUE_{number}",
        "number": number,
        "title": f"Issue {number}",
        "url": f"https://github.com/josys-src/frontend/issues/{number}",
        "state": state,
        "createdAt": f"2026-01-{number:02d}T00:00:00Z",
        "updatedAt": f"2026-02-{number:02d}T00:00:00Z",
        "closedAt": f"2026-02-{number:02d}T00:00:00Z" if state == "CLOSED" else None,
        "comments": {"totalCount": number},
        "labels": {"nodes": [{"name": "bug"}, None]},
        "repository": {"nameWithOwner": "josys-src/frontend"},
    }


def issue_page(
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
async def test_issue_collector_paginates_and_normalizes() -> None:
    graphql = StubGraphQL(
        [
            issue_page([issue_node(1)], has_next_page=True, cursor="next", issue_count=2),
            issue_page(
                [issue_node(2, state="CLOSED")],
                has_next_page=False,
                cursor=None,
                issue_count=2,
            ),
        ]
    )

    result = await IssueCollector(graphql).collect(  # type: ignore[arg-type]
        "josys-src",
        ("frontend",),
        "octocat",
    )

    assert [item.number for item in result.issues] == [1, 2]
    assert result.issues[0].state is IssueState.OPEN
    assert result.issues[0].labels == ("bug",)
    assert result.issues[1].comment_count == 2
    assert [variables["cursor"] for variables in graphql.variables] == [None, "next"]
    assert result.stats.api_requests == 2


@pytest.mark.anyio
async def test_issue_collector_warns_about_truncated_search() -> None:
    graphql = StubGraphQL(
        [issue_page([issue_node(1)], has_next_page=False, cursor=None, issue_count=2)]
    )

    result = await IssueCollector(graphql).collect(  # type: ignore[arg-type]
        "josys-src",
        ("frontend",),
        "octocat",
    )

    assert len(result.stats.warnings) == 1
    assert "returned 1 of 2" in result.stats.warnings[0]


@pytest.mark.anyio
async def test_issue_collector_checks_budget_before_next_repository() -> None:
    first = issue_page([], has_next_page=False, cursor=None, issue_count=0)
    first["rateLimit"]["remaining"] = 500  # type: ignore[index]
    graphql = StubGraphQL([first, issue_page([], has_next_page=False, cursor=None, issue_count=0)])

    with pytest.raises(RateLimitSafetyError):
        await IssueCollector(graphql, rate_limit_reserve=500).collect(  # type: ignore[arg-type]
            "josys-src",
            ("one", "two"),
            "octocat",
        )

    assert len(graphql.variables) == 1
