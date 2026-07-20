"""High-level orchestration for GitHub data access."""

from __future__ import annotations

from gitscope.github.errors import GraphQLQueryError
from gitscope.github.graphql import GitHubGraphQLClient
from gitscope.github.models import AuthenticatedUser, RepositoryDiscovery
from gitscope.github.rest import GitHubRESTClient


class GitHubService:
    """Expose GitScope operations while keeping API-specific details isolated."""

    def __init__(self, graphql: GitHubGraphQLClient, rest: GitHubRESTClient) -> None:
        self.graphql = graphql
        self.rest = rest

    async def authenticated_user(self) -> AuthenticatedUser:
        """Validate credentials and return their GitHub identity."""
        return await self.rest.authenticated_user()

    async def organization_repositories(
        self,
        organization: str,
        *,
        refresh: bool = False,
    ) -> RepositoryDiscovery:
        """Discover repositories through GraphQL, with REST as a targeted fallback."""
        try:
            return await self.graphql.organization_repositories(
                organization,
                refresh=refresh,
            )
        except GraphQLQueryError:
            repositories = await self.rest.organization_repositories(organization)
            return RepositoryDiscovery(repositories=repositories, source="rest")
