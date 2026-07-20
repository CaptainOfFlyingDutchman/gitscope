"""End-to-end construction of the versioned career report."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from gitscope.analytics.prs import summarize_pull_requests
from gitscope.analytics.reviews import summarize_reviews
from gitscope.cache import JsonCache
from gitscope.config import Settings
from gitscope.github.collection import CollectionStats
from gitscope.github.discovery import DiscoveryContext, discover_repositories
from gitscope.github.graphql import GitHubGraphQLClient
from gitscope.github.http import GitHubHTTPClient
from gitscope.github.prs import PullRequestCollector
from gitscope.github.reviews import ReviewCollector
from gitscope.models.report import (
    CareerReport,
    CollectionMetadata,
    ReportIdentity,
    ReportRepository,
)
from gitscope.report.json import write_json_report
from gitscope.repository_scope import RepositoryScope


@dataclass(frozen=True, slots=True)
class GeneratedCareerReport:
    """Report output and context needed for the CLI summary."""

    report: CareerReport
    path: Path
    discovery_context: DiscoveryContext


async def generate_career_report(
    settings: Settings,
    repository_scope: RepositoryScope,
    *,
    refresh: bool = False,
    rate_limit_reserve: int = 500,
) -> GeneratedCareerReport:
    """Collect scoped GitHub contributions and atomically write report.json."""
    context = await discover_repositories(
        settings,
        repository_scope.names,
        refresh=refresh,
    )
    stats = _discovery_stats(context)
    cache = JsonCache(settings.cache_directory / "graphql")
    async with GitHubHTTPClient(settings.github_token) as http:
        graphql = GitHubGraphQLClient(http, cache)
        pull_request_collection = await PullRequestCollector(
            graphql,
            rate_limit_reserve=rate_limit_reserve,
        ).collect(
            settings.organization,
            repository_scope.names,
            settings.username,
            refresh=refresh,
        )
        stats.merge(pull_request_collection.stats)
        review_collection = await ReviewCollector(
            graphql,
            rate_limit_reserve=rate_limit_reserve,
        ).collect(
            settings.organization,
            repository_scope.names,
            settings.username,
            refresh=refresh,
        )
        stats.merge(review_collection.stats)

    report = CareerReport(
        organization=settings.organization,
        identity=ReportIdentity(
            username=settings.username,
            authenticated_as=context.authenticated_user.login,
        ),
        collection=CollectionMetadata(
            generated_at=datetime.now(UTC),
            repository_scope_file=str(repository_scope.source),
            repository_count=len(context.discovery.repositories),
            github_api_requests=stats.api_requests,
            github_cache_hits=stats.cache_hits,
            graphql_rate_limit_remaining=(
                stats.latest_rate_limit.remaining if stats.latest_rate_limit else None
            ),
            graphql_rate_limit_reset_at=(
                stats.latest_rate_limit.reset_at if stats.latest_rate_limit else None
            ),
            warnings=tuple(stats.warnings),
        ),
        repositories=tuple(
            ReportRepository(
                name_with_owner=repository.name_with_owner,
                url=repository.url,
                visibility=repository.visibility,
                is_archived=repository.is_archived,
                is_fork=repository.is_fork,
                default_branch=repository.default_branch,
                primary_language=repository.primary_language,
                stars=repository.stars,
                forks=repository.forks,
            )
            for repository in context.discovery.repositories
        ),
        pull_request_summary=summarize_pull_requests(pull_request_collection.pull_requests),
        review_summary=summarize_reviews(review_collection.reviews),
        pull_requests=pull_request_collection.pull_requests,
        reviews=review_collection.reviews,
    )
    path = write_json_report(report, settings.output_directory)
    return GeneratedCareerReport(report=report, path=path, discovery_context=context)


def _discovery_stats(context: DiscoveryContext) -> CollectionStats:
    discovery = context.discovery
    stats = CollectionStats(
        api_requests=discovery.api_requests + 1,
        cache_hits=discovery.cache_hits,
    )
    if not discovery.from_cache:
        stats.latest_rate_limit = discovery.rate_limit
    return stats
