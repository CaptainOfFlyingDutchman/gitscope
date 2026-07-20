"""Collection of issues authored by the target user."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from gitscope.github.collection import CollectionStats
from gitscope.github.errors import InvalidGitHubResponseError
from gitscope.github.graphql import GitHubGraphQLClient
from gitscope.github.models import RateLimit
from gitscope.models.issue import Issue, IssueState

AUTHORED_ISSUES_QUERY = """
query AuthoredIssues($query: String!, $cursor: String) {
  search(query: $query, type: ISSUE, first: 100, after: $cursor) {
    issueCount
    nodes {
      ... on Issue {
        id
        number
        title
        url
        state
        createdAt
        updatedAt
        closedAt
        comments { totalCount }
        labels(first: 100) { nodes { name } }
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


class _CountConnection(_GitHubModel):
    total_count: int = Field(alias="totalCount")


class _Label(_GitHubModel):
    name: str


class _LabelConnection(_GitHubModel):
    nodes: list[_Label | None]


class _IssueNode(_GitHubModel):
    node_id: str = Field(alias="id")
    number: int
    title: str
    url: str
    state: IssueState
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    closed_at: datetime | None = Field(alias="closedAt")
    comments: _CountConnection
    labels: _LabelConnection
    repository: _Repository

    def to_domain(self) -> Issue:
        return Issue(
            node_id=self.node_id,
            repository=self.repository.name_with_owner,
            number=self.number,
            title=self.title,
            url=self.url,
            state=self.state,
            created_at=self.created_at,
            updated_at=self.updated_at,
            closed_at=self.closed_at,
            comment_count=self.comments.total_count,
            labels=tuple(sorted(label.name for label in self.labels.nodes if label is not None)),
        )


class _SearchConnection(_GitHubModel):
    issue_count: int = Field(alias="issueCount")
    nodes: list[_IssueNode | None]
    page_info: _PageInfo = Field(alias="pageInfo")


class _IssuePage(_GitHubModel):
    search: _SearchConnection
    rate_limit: RateLimit = Field(alias="rateLimit")


@dataclass(frozen=True, slots=True)
class IssueCollection:
    """Authored issues and collection accounting."""

    issues: tuple[Issue, ...]
    stats: CollectionStats


class IssueCollector:
    """Collect authored issues within explicitly allowlisted repositories."""

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
    ) -> IssueCollection:
        """Collect every authored issue returned by GitHub search for the allowlist."""
        issues: dict[str, Issue] = {}
        stats = CollectionStats()
        for repository_name in repository_names:
            cursor: str | None = None
            repository_total = 0
            while True:
                data, from_cache = await self.graphql.execute(
                    AUTHORED_ISSUES_QUERY,
                    {
                        "query": (
                            f"repo:{organization}/{repository_name} is:issue author:{username}"
                        ),
                        "cursor": cursor,
                    },
                    refresh=refresh,
                )
                page = self._parse_page(data)
                stats.record(page.rate_limit, from_cache=from_cache)
                nodes = [node for node in page.search.nodes if node is not None]
                repository_total += len(nodes)
                for node in nodes:
                    issues[node.node_id] = node.to_domain()

                if not page.search.page_info.has_next_page:
                    if repository_total < page.search.issue_count:
                        stats.warnings.append(
                            f"GitHub search returned {repository_total} of "
                            f"{page.search.issue_count} authored issues for "
                            f"{organization}/{repository_name}."
                        )
                    break
                stats.require_budget(self.rate_limit_reserve)
                cursor = page.search.page_info.end_cursor
                if not cursor:
                    raise InvalidGitHubResponseError(
                        "GitHub indicated another issue page without a cursor."
                    )

        ordered = tuple(
            sorted(issues.values(), key=lambda item: (item.created_at, item.repository))
        )
        return IssueCollection(issues=ordered, stats=stats)

    @staticmethod
    def _parse_page(data: dict[str, object]) -> _IssuePage:
        try:
            return _IssuePage.model_validate(data)
        except ValidationError as exc:
            raise InvalidGitHubResponseError(
                "GitHub returned invalid authored-issue data."
            ) from exc
