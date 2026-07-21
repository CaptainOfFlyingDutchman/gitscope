"""Application-level GitHub repository discovery workflow."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from gitscope.cache import JsonCache
from gitscope.config import Settings
from gitscope.github.graphql import GitHubGraphQLClient
from gitscope.github.http import GitHubHTTPClient
from gitscope.github.models import AuthenticatedUser, RepositoryDiscovery
from gitscope.github.rest import GitHubRESTClient
from gitscope.github.service import GitHubService


@dataclass(frozen=True, slots=True)
class DiscoveryContext:
    """Authenticated identity and visible organization repositories."""

    authenticated_user: AuthenticatedUser
    discovery: RepositoryDiscovery


async def discover_repositories(
    settings: Settings,
    repository_names: tuple[str, ...] | None,
    *,
    refresh: bool = False,
) -> DiscoveryContext:
    """Validate the token and fetch the requested repository selection."""
    _prepare_cache_directory(settings.cache_directory)
    cache = JsonCache(settings.cache_directory / "graphql")
    async with GitHubHTTPClient(settings.github_token) as http:
        rest = GitHubRESTClient(http)
        graphql = GitHubGraphQLClient(http, cache)
        service = GitHubService(graphql, rest)
        authenticated_user = await service.authenticated_user()
        if repository_names is None:
            discovery = await service.organization_repositories(
                settings.organization,
                refresh=refresh,
            )
        else:
            discovery = await service.repositories_by_name(
                settings.organization,
                repository_names,
                refresh=refresh,
            )
    return DiscoveryContext(authenticated_user=authenticated_user, discovery=discovery)


def _prepare_cache_directory(cache_directory: Path) -> None:
    """Create private state directories without changing unrelated parent permissions."""
    state_directory = cache_directory.parent
    state_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    cache_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if state_directory.name == ".gitscope":
        os.chmod(state_directory, 0o700)
    os.chmod(cache_directory, 0o700)
