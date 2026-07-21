"""Low-cost detection of authored commits before cloning repository history."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from gitscope.github.collection import CollectionStats
from gitscope.github.errors import InvalidGitHubResponseError
from gitscope.github.graphql import GitHubGraphQLClient
from gitscope.github.models import RateLimit

COMMIT_PRESENCE_BATCH_SIZE = 25


class _GitHubModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class _CommitHistory(_GitHubModel):
    total_count: int = Field(alias="totalCount")


class _CommitTarget(_GitHubModel):
    history: _CommitHistory


class _DefaultBranch(_GitHubModel):
    target: _CommitTarget


class _Repository(_GitHubModel):
    name_with_owner: str = Field(alias="nameWithOwner")
    default_branch_ref: _DefaultBranch | None = Field(alias="defaultBranchRef")


@dataclass(frozen=True, slots=True)
class CommitPresenceCollection:
    """Repositories with authored default-branch commits and request accounting."""

    repositories: frozenset[str]
    stats: CollectionStats


class CommitPresenceCollector:
    """Find repositories worth cloning using batched default-branch history queries."""

    def __init__(self, graphql: GitHubGraphQLClient, *, rate_limit_reserve: int = 500) -> None:
        self.graphql = graphql
        self.rate_limit_reserve = rate_limit_reserve

    async def collect(
        self,
        organization: str,
        repository_names: tuple[str, ...],
        emails: frozenset[str],
        *,
        refresh: bool = False,
    ) -> CommitPresenceCollection:
        """Return repositories with authored commits reachable from their default branch."""
        repositories: set[str] = set()
        stats = CollectionStats()
        ordered_emails = sorted(emails)
        for start in range(0, len(repository_names), COMMIT_PRESENCE_BATCH_SIZE):
            stats.require_budget(self.rate_limit_reserve)
            batch = repository_names[start : start + COMMIT_PRESENCE_BATCH_SIZE]
            query, variables = _build_query(organization, batch, ordered_emails)
            data, from_cache = await self.graphql.execute(
                query,
                variables,
                refresh=refresh,
            )
            rate_limit = _parse_rate_limit(data)
            stats.record(rate_limit, from_cache=from_cache)
            for index in range(len(batch)):
                repository = _parse_repository(data, f"repo{index}")
                if (
                    repository is not None
                    and repository.default_branch_ref is not None
                    and repository.default_branch_ref.target.history.total_count > 0
                ):
                    repositories.add(repository.name_with_owner)
        return CommitPresenceCollection(frozenset(repositories), stats)


def _build_query(
    organization: str,
    repository_names: tuple[str, ...],
    emails: list[str],
) -> tuple[str, dict[str, object]]:
    definitions = ["$owner: String!", "$emails: [String!]!"]
    fields: list[str] = []
    variables: dict[str, object] = {"owner": organization, "emails": emails}
    for index, repository_name in enumerate(repository_names):
        variable = f"name{index}"
        definitions.append(f"${variable}: String!")
        variables[variable] = repository_name
        fields.append(
            f"""
  repo{index}: repository(owner: $owner, name: ${variable}) {{
    nameWithOwner
    defaultBranchRef {{
      target {{
        ... on Commit {{
          history(first: 1, author: {{emails: $emails}}) {{ totalCount }}
        }}
      }}
    }}
  }}"""
        )
    query = (
        f"query CommitPresence({', '.join(definitions)}) {{"
        + "".join(fields)
        + "\n  rateLimit { cost remaining resetAt }\n}\n"
    )
    return query, variables


def _parse_rate_limit(data: dict[str, object]) -> RateLimit:
    try:
        return RateLimit.model_validate(data.get("rateLimit"))
    except ValidationError as exc:
        raise InvalidGitHubResponseError(
            "GitHub returned invalid commit-presence rate-limit data."
        ) from exc


def _parse_repository(data: dict[str, object], alias: str) -> _Repository | None:
    value = data.get(alias)
    if value is None:
        return None
    try:
        return _Repository.model_validate(value)
    except ValidationError as exc:
        raise InvalidGitHubResponseError(
            "GitHub returned invalid commit-presence repository data."
        ) from exc
