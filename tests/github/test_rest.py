"""Tests for GitHub REST authentication and repository discovery."""

from typing import Any

import httpx
import pytest

from gitscope.github.errors import InvalidGitHubResponseError
from gitscope.github.http import GitHubHTTPClient
from gitscope.github.rest import GitHubRESTClient


def rest_repository(name: str, *, private: bool = False) -> dict[str, Any]:
    return {
        "node_id": f"R_{name}",
        "name": name,
        "full_name": f"josys-src/{name}",
        "owner": {"login": "josys-src"},
        "html_url": f"https://github.com/josys-src/{name}",
        "visibility": "private" if private else "public",
        "private": private,
        "archived": False,
        "fork": False,
        "default_branch": "main",
        "language": "Python",
        "stargazers_count": 3,
        "forks_count": 2,
        "size": 100,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "pushed_at": "2026-01-02T00:00:00Z",
    }


@pytest.mark.anyio
async def test_authenticated_user() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"login": "octocat", "id": 1, "name": "Octo Cat"},
            request=request,
        )
    )
    async with httpx.AsyncClient(transport=transport) as client:
        rest = GitHubRESTClient(GitHubHTTPClient("secret", client=client))
        user = await rest.authenticated_user()

    assert user.login == "octocat"
    assert user.database_id == 1


@pytest.mark.anyio
async def test_repository_discovery_follows_rest_pages() -> None:
    pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        pages.append(page)
        repositories = (
            [rest_repository(f"repository-{index}") for index in range(100)]
            if page == 1
            else [rest_repository("private-repository", private=True)]
        )
        return httpx.Response(200, json=repositories, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        rest = GitHubRESTClient(GitHubHTTPClient("secret", client=client))
        repositories = await rest.organization_repositories("josys-src")

    assert pages == [1, 2]
    assert len(repositories) == 101
    assert repositories[-1].is_private is True
    assert repositories[-1].name_with_owner == "josys-src/private-repository"


@pytest.mark.anyio
async def test_repository_discovery_rejects_invalid_collection() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"unexpected": True}, request=request)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        rest = GitHubRESTClient(GitHubHTTPClient("secret", client=client))
        with pytest.raises(InvalidGitHubResponseError):
            await rest.organization_repositories("josys-src")
