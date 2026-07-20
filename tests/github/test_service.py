"""Tests for high-level GitHub API orchestration."""

import httpx
import pytest

from gitscope.github.graphql import GitHubGraphQLClient
from gitscope.github.http import GitHubHTTPClient
from gitscope.github.rest import GitHubRESTClient
from gitscope.github.service import GitHubService
from tests.github.test_rest import rest_repository


@pytest.mark.anyio
async def test_graphql_query_error_falls_back_to_rest() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path == "/graphql":
            return httpx.Response(
                200,
                json={"errors": [{"message": "field temporarily unavailable"}]},
                request=request,
            )
        return httpx.Response(200, json=[rest_repository("fallback")], request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        http = GitHubHTTPClient("secret", client=client)
        service = GitHubService(GitHubGraphQLClient(http), GitHubRESTClient(http))
        result = await service.organization_repositories("josys-src")

    assert requests == ["/graphql", "/orgs/josys-src/repos"]
    assert result.source == "rest"
    assert [repository.name for repository in result.repositories] == ["fallback"]


@pytest.mark.anyio
async def test_allowlist_fallback_never_lists_entire_organization() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/graphql":
            return httpx.Response(
                200,
                json={"errors": [{"message": "query unavailable"}]},
                request=request,
            )
        return httpx.Response(200, json=rest_repository("frontend"), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        http = GitHubHTTPClient("secret", client=client)
        service = GitHubService(GitHubGraphQLClient(http), GitHubRESTClient(http))
        result = await service.repositories_by_name("josys-src", ("frontend",))

    assert paths == ["/graphql", "/repos/josys-src/frontend"]
    assert result.source == "rest-allowlist"
