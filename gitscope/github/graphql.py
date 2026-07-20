"""GraphQL-first GitHub repository collection."""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from gitscope.cache import JsonCache
from gitscope.github.errors import (
    GraphQLQueryError,
    InvalidGitHubResponseError,
    OrganizationNotFoundError,
    RateLimitError,
)
from gitscope.github.http import GitHubHTTPClient
from gitscope.github.models import (
    RateLimit,
    RepositoryDiscovery,
    RepositorySummary,
    RepositoryVisibility,
)

GRAPHQL_API_URL = "https://api.github.com/graphql"

ORGANIZATION_REPOSITORIES_QUERY = """
query OrganizationRepositories($login: String!, $cursor: String) {
  organization(login: $login) {
    repositories(first: 100, after: $cursor, orderBy: {field: NAME, direction: ASC}) {
      nodes {
        id
        name
        nameWithOwner
        url
        visibility
        isPrivate
        isArchived
        isFork
        defaultBranchRef { name }
        primaryLanguage { name }
        stargazerCount
        forkCount
        diskUsage
        createdAt
        updatedAt
        pushedAt
      }
      pageInfo { hasNextPage endCursor }
    }
  }
  rateLimit { cost remaining resetAt }
}
"""


class _GraphQLModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class _NamedValue(_GraphQLModel):
    name: str


class _PageInfo(_GraphQLModel):
    has_next_page: bool = Field(alias="hasNextPage")
    end_cursor: str | None = Field(alias="endCursor")


class _RepositoryNode(_GraphQLModel):
    node_id: str = Field(alias="id")
    name: str
    name_with_owner: str = Field(alias="nameWithOwner")
    url: str
    visibility: RepositoryVisibility
    is_private: bool = Field(alias="isPrivate")
    is_archived: bool = Field(alias="isArchived")
    is_fork: bool = Field(alias="isFork")
    default_branch_ref: _NamedValue | None = Field(alias="defaultBranchRef")
    primary_language: _NamedValue | None = Field(alias="primaryLanguage")
    stargazer_count: int = Field(alias="stargazerCount")
    fork_count: int = Field(alias="forkCount")
    disk_usage: int | None = Field(alias="diskUsage")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    pushed_at: datetime | None = Field(alias="pushedAt")

    def to_summary(self) -> RepositorySummary:
        return RepositorySummary(
            node_id=self.node_id,
            name=self.name,
            name_with_owner=self.name_with_owner,
            url=self.url,
            visibility=self.visibility,
            is_private=self.is_private,
            is_archived=self.is_archived,
            is_fork=self.is_fork,
            default_branch=self.default_branch_ref.name if self.default_branch_ref else None,
            primary_language=self.primary_language.name if self.primary_language else None,
            stars=self.stargazer_count,
            forks=self.fork_count,
            disk_usage_kib=self.disk_usage,
            created_at=self.created_at,
            updated_at=self.updated_at,
            pushed_at=self.pushed_at,
        )


class _RepositoryConnection(_GraphQLModel):
    nodes: list[_RepositoryNode]
    page_info: _PageInfo = Field(alias="pageInfo")


class _Organization(_GraphQLModel):
    repositories: _RepositoryConnection


class _RepositoriesPage(_GraphQLModel):
    organization: _Organization | None
    rate_limit: RateLimit = Field(alias="rateLimit")


class GitHubGraphQLClient:
    """Execute GitHub GraphQL queries and traverse repository pages."""

    def __init__(self, http: GitHubHTTPClient, cache: JsonCache | None = None) -> None:
        self.http = http
        self.cache = cache

    async def execute(
        self,
        query: str,
        variables: dict[str, Any],
        *,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Execute one query, honoring the private response cache."""
        key = JsonCache.key_for("graphql", {"query": query, "variables": variables})
        if self.cache and not refresh:
            cached = self.cache.get(key)
            if cached is not None:
                return cached

        payload, headers = await self.http.request_json(
            "POST",
            GRAPHQL_API_URL,
            json_body={"query": query, "variables": variables},
        )
        if not isinstance(payload, dict):
            raise InvalidGitHubResponseError("GitHub returned an invalid GraphQL response.")

        errors = payload.get("errors")
        if errors:
            if headers.get("x-ratelimit-remaining") == "0":
                raise RateLimitError()
            raise GraphQLQueryError(self._error_messages(errors))

        data = payload.get("data")
        if not isinstance(data, dict):
            raise InvalidGitHubResponseError("GitHub GraphQL response did not contain data.")

        if self.cache:
            with suppress(OSError):
                self.cache.set(key, data)
        return data

    async def organization_repositories(
        self,
        organization: str,
        *,
        refresh: bool = False,
    ) -> RepositoryDiscovery:
        """Return every organization repository visible to the authenticated user."""
        repositories: list[RepositorySummary] = []
        cursor: str | None = None
        latest_rate_limit: RateLimit | None = None

        while True:
            data = await self.execute(
                ORGANIZATION_REPOSITORIES_QUERY,
                {"login": organization, "cursor": cursor},
                refresh=refresh,
            )
            try:
                page = _RepositoriesPage.model_validate(data)
            except ValidationError as exc:
                raise InvalidGitHubResponseError(
                    "GitHub returned invalid organization repository data."
                ) from exc
            if page.organization is None:
                raise OrganizationNotFoundError(
                    f"Organization '{organization}' was not found or is not visible to this token."
                )

            connection = page.organization.repositories
            repositories.extend(node.to_summary() for node in connection.nodes)
            latest_rate_limit = page.rate_limit
            if not connection.page_info.has_next_page:
                break
            cursor = connection.page_info.end_cursor
            if not cursor:
                raise InvalidGitHubResponseError(
                    "GitHub indicated another repository page without providing a cursor."
                )

        return RepositoryDiscovery(
            repositories=tuple(repositories),
            source="graphql",
            rate_limit=latest_rate_limit,
        )

    @staticmethod
    def _error_messages(errors: Any) -> str:
        if not isinstance(errors, list):
            return "GitHub GraphQL query failed."
        messages = [
            error["message"]
            for error in errors
            if isinstance(error, dict) and isinstance(error.get("message"), str)
        ]
        return "; ".join(messages) or "GitHub GraphQL query failed."
