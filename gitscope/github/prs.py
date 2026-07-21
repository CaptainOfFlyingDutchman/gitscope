"""Collection of pull requests authored by the target user."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from gitscope.date_range import LIFETIME_DATE_RANGE, DateRange
from gitscope.github.collection import CollectionStats
from gitscope.github.errors import InvalidGitHubResponseError
from gitscope.github.graphql import GitHubGraphQLClient
from gitscope.github.models import RateLimit
from gitscope.models.pull_request import PullRequest, PullRequestState

AUTHORED_PULL_REQUESTS_QUERY = """
query AuthoredPullRequests($query: String!, $cursor: String) {
  search(query: $query, type: ISSUE, first: 100, after: $cursor) {
    issueCount
    nodes {
      ... on PullRequest {
        id
        number
        title
        url
        state
        isDraft
        createdAt
        updatedAt
        closedAt
        mergedAt
        additions
        deletions
        changedFiles
        commits(first: 1) { totalCount }
        repository { nameWithOwner }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
  rateLimit { cost remaining resetAt }
}
"""


class _GitHubModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class _PageInfo(_GitHubModel):
    has_next_page: bool = Field(alias="hasNextPage")
    end_cursor: str | None = Field(alias="endCursor")


class _Repository(_GitHubModel):
    name_with_owner: str = Field(alias="nameWithOwner")


class _CommitConnection(_GitHubModel):
    total_count: int = Field(alias="totalCount")


class _PullRequestNode(_GitHubModel):
    node_id: str = Field(alias="id")
    number: int
    title: str
    url: str
    state: PullRequestState
    is_draft: bool = Field(alias="isDraft")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    closed_at: datetime | None = Field(alias="closedAt")
    merged_at: datetime | None = Field(alias="mergedAt")
    additions: int
    deletions: int
    changed_files: int = Field(alias="changedFiles")
    commits: _CommitConnection
    repository: _Repository

    def to_domain(self) -> PullRequest:
        return PullRequest(
            node_id=self.node_id,
            repository=self.repository.name_with_owner,
            number=self.number,
            title=self.title,
            url=self.url,
            state=self.state,
            is_draft=self.is_draft,
            created_at=self.created_at,
            updated_at=self.updated_at,
            closed_at=self.closed_at,
            merged_at=self.merged_at,
            additions=self.additions,
            deletions=self.deletions,
            changed_files=self.changed_files,
            commit_count=self.commits.total_count,
        )


class _SearchConnection(_GitHubModel):
    issue_count: int = Field(alias="issueCount")
    nodes: list[_PullRequestNode | None]
    page_info: _PageInfo = Field(alias="pageInfo")


class _PullRequestPage(_GitHubModel):
    search: _SearchConnection
    rate_limit: RateLimit = Field(alias="rateLimit")


@dataclass(frozen=True, slots=True)
class PullRequestCollection:
    """Authored pull requests and collection accounting."""

    pull_requests: tuple[PullRequest, ...]
    stats: CollectionStats


class PullRequestCollector:
    """Collect authored pull requests within explicitly allowlisted repositories."""

    def __init__(self, graphql: GitHubGraphQLClient, *, rate_limit_reserve: int = 500) -> None:
        self.graphql = graphql
        self.rate_limit_reserve = rate_limit_reserve

    async def collect(
        self,
        organization: str,
        repository_names: tuple[str, ...],
        username: str,
        *,
        refresh: bool = False,
        organization_wide: bool = False,
        date_range: DateRange = LIFETIME_DATE_RANGE,
    ) -> PullRequestCollection:
        """Collect authored PRs for an allowlist or the visible organization scope."""
        pull_requests: dict[str, PullRequest] = {}
        stats = CollectionStats()
        scopes: tuple[str | None, ...] = (None,) if organization_wide else repository_names
        for repository_name in scopes:
            cursor: str | None = None
            repository_total = 0
            while True:
                stats.require_budget(self.rate_limit_reserve)
                scope = (
                    f"org:{organization}"
                    if repository_name is None
                    else f"repo:{organization}/{repository_name}"
                )
                qualifier = date_range.search_qualifier
                query = f"{scope} is:pr author:{username}"
                if qualifier:
                    query = f"{query} {qualifier}"
                data, from_cache = await self.graphql.execute(
                    AUTHORED_PULL_REQUESTS_QUERY,
                    {
                        "query": query,
                        "cursor": cursor,
                    },
                    refresh=refresh,
                )
                page = self._parse_page(data)
                stats.record(page.rate_limit, from_cache=from_cache)
                nodes = [node for node in page.search.nodes if node is not None]
                repository_total += len(nodes)
                for node in nodes:
                    pull_requests[node.node_id] = node.to_domain()

                if not page.search.page_info.has_next_page:
                    if repository_total < page.search.issue_count:
                        stats.warnings.append(
                            f"GitHub search returned {repository_total} of "
                            f"{page.search.issue_count} authored pull requests for "
                            f"{scope}."
                        )
                    break
                cursor = page.search.page_info.end_cursor
                if not cursor:
                    raise InvalidGitHubResponseError(
                        "GitHub indicated another pull-request page without a cursor."
                    )

        ordered = tuple(
            sorted(
                (item for item in pull_requests.values() if date_range.contains(item.created_at)),
                key=lambda item: (item.created_at, item.repository),
            )
        )
        return PullRequestCollection(pull_requests=ordered, stats=stats)

    @staticmethod
    def _parse_page(data: dict[str, object]) -> _PullRequestPage:
        try:
            return _PullRequestPage.model_validate(data)
        except ValidationError as exc:
            raise InvalidGitHubResponseError(
                "GitHub returned invalid authored pull-request data."
            ) from exc
