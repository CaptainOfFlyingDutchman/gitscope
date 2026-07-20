"""Collection of pull-request reviews submitted by the target user."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from gitscope.github.collection import CollectionStats
from gitscope.github.errors import InvalidGitHubResponseError
from gitscope.github.graphql import GitHubGraphQLClient
from gitscope.github.models import RateLimit
from gitscope.models.review import PullRequestReview, ReviewState

REVIEWED_PULL_REQUESTS_QUERY = """
query ReviewedPullRequests($query: String!, $username: String!, $cursor: String) {
  search(query: $query, type: ISSUE, first: 100, after: $cursor) {
    issueCount
    nodes {
      ... on PullRequest {
        id
        number
        title
        url
        repository { nameWithOwner }
        reviews(first: 100, author: $username) {
          nodes { id state createdAt submittedAt url }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
  rateLimit { cost remaining resetAt }
}
"""

PULL_REQUEST_REVIEWS_PAGE_QUERY = """
query PullRequestReviewsPage($id: ID!, $username: String!, $cursor: String!) {
  node(id: $id) {
    ... on PullRequest {
      reviews(first: 100, after: $cursor, author: $username) {
        nodes { id state createdAt submittedAt url }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
  rateLimit { cost remaining resetAt }
}
"""

GITHUB_SEARCH_RESULT_LIMIT = 1000
GITHUB_LAUNCH_DATE = date(2008, 4, 10)


class _GitHubModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class _PageInfo(_GitHubModel):
    has_next_page: bool = Field(alias="hasNextPage")
    end_cursor: str | None = Field(alias="endCursor")


class _Repository(_GitHubModel):
    name_with_owner: str = Field(alias="nameWithOwner")


class _ReviewNode(_GitHubModel):
    node_id: str = Field(alias="id")
    state: ReviewState
    created_at: datetime = Field(alias="createdAt")
    submitted_at: datetime | None = Field(alias="submittedAt")
    url: str


class _ReviewConnection(_GitHubModel):
    nodes: list[_ReviewNode | None]
    page_info: _PageInfo = Field(alias="pageInfo")


class _PullRequestNode(_GitHubModel):
    node_id: str = Field(alias="id")
    number: int
    title: str
    url: str
    repository: _Repository
    reviews: _ReviewConnection


class _SearchConnection(_GitHubModel):
    issue_count: int = Field(alias="issueCount")
    nodes: list[_PullRequestNode | None]
    page_info: _PageInfo = Field(alias="pageInfo")


class _ReviewedPullRequestsPage(_GitHubModel):
    search: _SearchConnection
    rate_limit: RateLimit = Field(alias="rateLimit")


class _PullRequestReviewsNode(_GitHubModel):
    reviews: _ReviewConnection


class _PullRequestReviewsPage(_GitHubModel):
    node: _PullRequestReviewsNode | None
    rate_limit: RateLimit = Field(alias="rateLimit")


@dataclass(frozen=True, slots=True)
class ReviewCollection:
    """Submitted reviews and collection accounting."""

    reviews: tuple[PullRequestReview, ...]
    stats: CollectionStats


@dataclass(frozen=True, slots=True)
class _DateWindow:
    start: date
    end: date

    def split(self) -> tuple[_DateWindow, _DateWindow] | None:
        if self.start >= self.end:
            return None
        midpoint = self.start + (self.end - self.start) // 2
        return (
            _DateWindow(self.start, midpoint),
            _DateWindow(midpoint + timedelta(days=1), self.end),
        )

    @property
    def qualifier(self) -> str:
        return f"created:{self.start.isoformat()}..{self.end.isoformat()}"


class ReviewCollector:
    """Collect reviews submitted within explicitly allowlisted repositories."""

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
    ) -> ReviewCollection:
        """Collect all reviews authored by the target user for allowlisted repositories."""
        reviews: dict[str, PullRequestReview] = {}
        stats = CollectionStats()
        for repository_name in repository_names:
            await self._collect_search_window(
                reviews,
                stats,
                organization,
                repository_name,
                username,
                window=None,
                refresh=refresh,
            )

        ordered = tuple(
            sorted(
                reviews.values(),
                key=lambda item: (item.submitted_at or item.created_at, item.repository),
            )
        )
        return ReviewCollection(reviews=ordered, stats=stats)

    async def _collect_search_window(
        self,
        reviews: dict[str, PullRequestReview],
        stats: CollectionStats,
        organization: str,
        repository_name: str,
        username: str,
        *,
        window: _DateWindow | None,
        refresh: bool,
    ) -> None:
        cursor: str | None = None
        candidate_total = 0
        while True:
            query = f"repo:{organization}/{repository_name} is:pr reviewed-by:{username}"
            if window is not None:
                query = f"{query} {window.qualifier}"
            data, from_cache = await self.graphql.execute(
                REVIEWED_PULL_REQUESTS_QUERY,
                {"query": query, "username": username, "cursor": cursor},
                refresh=refresh,
            )
            page = self._parse_search_page(data)
            stats.record(page.rate_limit, from_cache=from_cache)

            if cursor is None and page.search.issue_count > GITHUB_SEARCH_RESULT_LIMIT:
                effective_window = window or _DateWindow(
                    GITHUB_LAUNCH_DATE,
                    datetime.now(UTC).date(),
                )
                partitions = effective_window.split()
                if partitions is not None:
                    stats.require_budget(self.rate_limit_reserve)
                    for partition in partitions:
                        await self._collect_search_window(
                            reviews,
                            stats,
                            organization,
                            repository_name,
                            username,
                            window=partition,
                            refresh=refresh,
                        )
                    return

            pull_requests = [node for node in page.search.nodes if node is not None]
            candidate_total += len(pull_requests)
            for pull_request in pull_requests:
                self._add_reviews(reviews, pull_request, pull_request.reviews.nodes)
                await self._collect_remaining_reviews(
                    reviews,
                    stats,
                    pull_request,
                    username,
                    refresh=refresh,
                )

            if not page.search.page_info.has_next_page:
                if candidate_total < page.search.issue_count:
                    effective_window = window or _DateWindow(
                        GITHUB_LAUNCH_DATE,
                        datetime.now(UTC).date(),
                    )
                    partitions = effective_window.split()
                    if partitions is not None:
                        stats.require_budget(self.rate_limit_reserve)
                        for partition in partitions:
                            await self._collect_search_window(
                                reviews,
                                stats,
                                organization,
                                repository_name,
                                username,
                                window=partition,
                                refresh=refresh,
                            )
                        return
                    qualifier = f" in {window.qualifier}" if window else ""
                    stats.warnings.append(
                        f"GitHub search returned {candidate_total} of "
                        f"{page.search.issue_count} reviewed pull requests for "
                        f"{organization}/{repository_name}{qualifier}."
                    )
                return
            stats.require_budget(self.rate_limit_reserve)
            cursor = page.search.page_info.end_cursor
            if not cursor:
                raise InvalidGitHubResponseError(
                    "GitHub indicated another reviewed pull-request page without a cursor."
                )

    async def _collect_remaining_reviews(
        self,
        reviews: dict[str, PullRequestReview],
        stats: CollectionStats,
        pull_request: _PullRequestNode,
        username: str,
        *,
        refresh: bool,
    ) -> None:
        cursor = pull_request.reviews.page_info.end_cursor
        has_next_page = pull_request.reviews.page_info.has_next_page
        while has_next_page:
            if not cursor:
                raise InvalidGitHubResponseError(
                    "GitHub indicated another review page without a cursor."
                )
            stats.require_budget(self.rate_limit_reserve)
            data, from_cache = await self.graphql.execute(
                PULL_REQUEST_REVIEWS_PAGE_QUERY,
                {"id": pull_request.node_id, "username": username, "cursor": cursor},
                refresh=refresh,
            )
            page = self._parse_reviews_page(data)
            stats.record(page.rate_limit, from_cache=from_cache)
            if page.node is None:
                raise InvalidGitHubResponseError(
                    "A pull request disappeared while its reviews were being collected."
                )
            self._add_reviews(reviews, pull_request, page.node.reviews.nodes)
            has_next_page = page.node.reviews.page_info.has_next_page
            cursor = page.node.reviews.page_info.end_cursor

    @staticmethod
    def _add_reviews(
        destination: dict[str, PullRequestReview],
        pull_request: _PullRequestNode,
        review_nodes: list[_ReviewNode | None],
    ) -> None:
        for review in review_nodes:
            if review is None:
                continue
            destination[review.node_id] = PullRequestReview(
                node_id=review.node_id,
                repository=pull_request.repository.name_with_owner,
                pull_request_number=pull_request.number,
                pull_request_title=pull_request.title,
                pull_request_url=pull_request.url,
                state=review.state,
                created_at=review.created_at,
                submitted_at=review.submitted_at,
                url=review.url,
            )

    @staticmethod
    def _parse_search_page(data: dict[str, object]) -> _ReviewedPullRequestsPage:
        try:
            return _ReviewedPullRequestsPage.model_validate(data)
        except ValidationError as exc:
            raise InvalidGitHubResponseError(
                "GitHub returned invalid reviewed pull-request data."
            ) from exc

    @staticmethod
    def _parse_reviews_page(data: dict[str, object]) -> _PullRequestReviewsPage:
        try:
            return _PullRequestReviewsPage.model_validate(data)
        except ValidationError as exc:
            raise InvalidGitHubResponseError(
                "GitHub returned invalid pull-request review data."
            ) from exc
