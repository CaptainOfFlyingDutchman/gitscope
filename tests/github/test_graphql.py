"""Tests for GraphQL repository discovery."""

from pathlib import Path
from typing import Any

import httpx
import pytest

from gitscope.cache import JsonCache
from gitscope.github.errors import GraphQLQueryError, OrganizationNotFoundError
from gitscope.github.graphql import GitHubGraphQLClient


def repository_node(name: str, *, private: bool = False) -> dict[str, Any]:
    return {
        "id": f"R_{name}",
        "name": name,
        "nameWithOwner": f"josys-src/{name}",
        "url": f"https://github.com/josys-src/{name}",
        "visibility": "PRIVATE" if private else "PUBLIC",
        "isPrivate": private,
        "isArchived": False,
        "isFork": False,
        "defaultBranchRef": {"name": "main"},
        "primaryLanguage": {"name": "Python"},
        "stargazerCount": 1,
        "forkCount": 2,
        "diskUsage": 42,
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
        "pushedAt": "2026-01-02T00:00:00Z",
    }


def graphql_page(
    nodes: list[dict[str, Any]],
    *,
    has_next_page: bool,
    cursor: str | None,
) -> dict[str, Any]:
    return {
        "data": {
            "organization": {
                "repositories": {
                    "nodes": nodes,
                    "pageInfo": {"hasNextPage": has_next_page, "endCursor": cursor},
                }
            },
            "rateLimit": {
                "cost": 1,
                "remaining": 4999,
                "resetAt": "2026-07-20T12:00:00Z",
            },
        }
    }


@pytest.mark.anyio
async def test_repository_discovery_follows_graphql_cursors() -> None:
    cursors: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        import json

        variables = json.loads(body)["variables"]
        cursors.append(variables["cursor"])
        if variables["cursor"] is None:
            return httpx.Response(
                200,
                json=graphql_page(
                    [repository_node("one")],
                    has_next_page=True,
                    cursor="next-page",
                ),
            )
        return httpx.Response(
            200,
            json=graphql_page(
                [repository_node("two", private=True)],
                has_next_page=False,
                cursor=None,
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        from gitscope.github.http import GitHubHTTPClient

        http = GitHubHTTPClient("secret", client=client)
        result = await GitHubGraphQLClient(http).organization_repositories("josys-src")

    assert cursors == [None, "next-page"]
    assert [repository.name for repository in result.repositories] == ["one", "two"]
    assert result.repositories[1].is_private is True
    assert result.source == "graphql"
    assert result.rate_limit is not None
    assert result.rate_limit.remaining == 4999


@pytest.mark.anyio
async def test_execute_uses_cache(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json=graphql_page([], has_next_page=False, cursor=None),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        from gitscope.github.http import GitHubHTTPClient

        http = GitHubHTTPClient("secret", client=client)
        graphql = GitHubGraphQLClient(http, JsonCache(tmp_path))
        await graphql.organization_repositories("josys-src")
        await graphql.organization_repositories("josys-src")

    assert calls == 1


@pytest.mark.anyio
async def test_execute_reports_graphql_errors() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, json={"errors": [{"message": "query failed"}]})
    )
    async with httpx.AsyncClient(transport=transport) as client:
        from gitscope.github.http import GitHubHTTPClient

        graphql = GitHubGraphQLClient(GitHubHTTPClient("secret", client=client))
        with pytest.raises(GraphQLQueryError, match="query failed"):
            await graphql.organization_repositories("josys-src")


@pytest.mark.anyio
async def test_repository_discovery_reports_invisible_organization() -> None:
    payload = graphql_page([], has_next_page=False, cursor=None)
    payload["data"]["organization"] = None
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as client:
        from gitscope.github.http import GitHubHTTPClient

        graphql = GitHubGraphQLClient(GitHubHTTPClient("secret", client=client))
        with pytest.raises(OrganizationNotFoundError, match="josys-src"):
            await graphql.organization_repositories("josys-src")
