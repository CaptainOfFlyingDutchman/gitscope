"""Tests for server-side authored-commit presence detection."""

import json

import httpx
import pytest

from gitscope.date_range import DateRange
from gitscope.github.commit_presence import CommitPresenceCollector
from gitscope.github.errors import RateLimitSafetyError
from gitscope.github.graphql import GitHubGraphQLClient
from gitscope.github.http import GitHubHTTPClient


def _repository(name: str, total_count: int) -> dict[str, object]:
    return {
        "nameWithOwner": f"josys-src/{name}",
        "defaultBranchRef": {"target": {"history": {"totalCount": total_count}}},
    }


@pytest.mark.anyio
async def test_commit_presence_selects_only_repositories_with_authored_commits() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        assert "query CommitPresence" in body["query"]
        assert body["variables"] == {
            "owner": "josys-src",
            "emails": ["1+octocat@users.noreply.github.com", "octocat@example.com"],
            "name0": "active",
            "name1": "idle",
            "name2": "empty",
        }
        return httpx.Response(
            200,
            json={
                "data": {
                    "repo0": _repository("active", 3),
                    "repo1": _repository("idle", 0),
                    "repo2": {
                        "nameWithOwner": "josys-src/empty",
                        "defaultBranchRef": None,
                    },
                    "rateLimit": {
                        "cost": 4,
                        "remaining": 4995,
                        "resetAt": "2026-07-20T12:00:00Z",
                    },
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        collector = CommitPresenceCollector(
            GitHubGraphQLClient(GitHubHTTPClient("secret", client=client))
        )
        result = await collector.collect(
            "josys-src",
            ("active", "idle", "empty"),
            frozenset({"octocat@example.com", "1+octocat@users.noreply.github.com"}),
        )

    assert result.repositories == frozenset({"josys-src/active"})
    assert result.stats.api_requests == 1
    assert result.stats.latest_rate_limit is not None
    assert result.stats.latest_rate_limit.remaining == 4995


@pytest.mark.anyio
async def test_commit_presence_stops_before_crossing_rate_limit_reserve() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        body = json.loads(request.read())
        data = {
            f"repo{index}": _repository(name, 0)
            for index, name in enumerate(
                value for key, value in body["variables"].items() if key.startswith("name")
            )
        }
        data["rateLimit"] = {
            "cost": 26,
            "remaining": 500,
            "resetAt": "2026-07-20T12:00:00Z",
        }
        return httpx.Response(200, json={"data": data})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        collector = CommitPresenceCollector(
            GitHubGraphQLClient(GitHubHTTPClient("secret", client=client)),
            rate_limit_reserve=500,
        )
        with pytest.raises(RateLimitSafetyError):
            await collector.collect(
                "josys-src",
                tuple(f"repo-{index}" for index in range(26)),
                frozenset({"octocat@example.com"}),
            )

    assert request_count == 1


@pytest.mark.anyio
async def test_commit_presence_passes_utc_date_bounds() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        assert "since: $since" in body["query"]
        assert "until: $until" in body["query"]
        assert body["variables"]["since"] == "2025-01-01T00:00:00Z"
        assert body["variables"]["until"].startswith("2025-12-31T23:59:59.999999")
        return httpx.Response(
            200,
            json={
                "data": {
                    "repo0": _repository("active", 1),
                    "rateLimit": {
                        "cost": 2,
                        "remaining": 4998,
                        "resetAt": "2026-07-20T12:00:00Z",
                    },
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await CommitPresenceCollector(
            GitHubGraphQLClient(GitHubHTTPClient("secret", client=client))
        ).collect(
            "josys-src",
            ("active",),
            frozenset({"octocat@example.com"}),
            date_range=DateRange.parse("2025-01-01", "2025-12-31"),
        )

    assert result.repositories == frozenset({"josys-src/active"})
