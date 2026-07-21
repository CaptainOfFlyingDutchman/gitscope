"""End-to-end construction of the versioned career report."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from gitscope.analytics.commits import summarize_commits
from gitscope.analytics.issues import summarize_issues
from gitscope.analytics.prs import summarize_pull_requests
from gitscope.analytics.repositories import summarize_languages, summarize_repositories
from gitscope.analytics.reviews import summarize_reviews
from gitscope.analytics.timeline import build_timeline
from gitscope.cache import JsonCache
from gitscope.charts import write_chart_bundle
from gitscope.config import Settings
from gitscope.git.collection import collect_git_contributions
from gitscope.git.identities import DEFAULT_IDENTITIES_FILE, AuthorIdentities
from gitscope.github.collection import CollectionStats
from gitscope.github.commit_presence import CommitPresenceCollector
from gitscope.github.discovery import DiscoveryContext, discover_repositories
from gitscope.github.graphql import GitHubGraphQLClient
from gitscope.github.http import GitHubHTTPClient
from gitscope.github.issues import IssueCollector
from gitscope.github.prs import PullRequestCollector
from gitscope.github.reviews import ReviewCollector
from gitscope.models.issue import Issue
from gitscope.models.pull_request import PullRequest
from gitscope.models.report import (
    CareerReport,
    CollectionMetadata,
    ReportIdentity,
    ReportRepository,
)
from gitscope.models.review import PullRequestReview
from gitscope.report.csv import write_csv_report
from gitscope.report.html import write_html_report
from gitscope.report.json import write_json_report
from gitscope.report.markdown import write_markdown_report
from gitscope.repository_scope import RepositoryScope


@dataclass(frozen=True, slots=True)
class GeneratedCareerReport:
    """Report output and context needed for the CLI summary."""

    report: CareerReport
    path: Path
    discovery_context: DiscoveryContext
    chart_paths: tuple[Path, ...] = ()
    html_path: Path | None = None
    markdown_path: Path | None = None
    csv_path: Path | None = None


async def generate_career_report(
    settings: Settings,
    repository_scope: RepositoryScope,
    *,
    refresh: bool = False,
    rate_limit_reserve: int = 500,
    identities_file: Path = DEFAULT_IDENTITIES_FILE,
    git_concurrency: int = 4,
    scope_observer: Callable[[DiscoveryContext], None] | None = None,
    git_scope_observer: Callable[[int, int], None] | None = None,
) -> GeneratedCareerReport:
    """Collect scoped GitHub contributions and atomically write report.json."""
    context = await discover_repositories(
        settings,
        None if repository_scope.all_repositories else repository_scope.names,
        refresh=refresh,
    )
    if scope_observer is not None:
        scope_observer(context)
    repository_names = tuple(repository.name for repository in context.discovery.repositories)
    identities = AuthorIdentities.build(
        username=settings.username,
        database_id=context.authenticated_user.database_id,
        github_name=context.authenticated_user.name,
        source=identities_file,
    )
    stats = _discovery_stats(context)
    contributed_repositories: frozenset[str] | None = None
    cache = JsonCache(settings.cache_directory / "graphql")
    async with GitHubHTTPClient(settings.github_token) as http:
        graphql = GitHubGraphQLClient(http, cache)
        pull_request_collection = await PullRequestCollector(
            graphql,
            rate_limit_reserve=rate_limit_reserve,
        ).collect(
            settings.organization,
            repository_names,
            settings.username,
            refresh=refresh,
            organization_wide=repository_scope.all_repositories,
        )
        stats.merge(pull_request_collection.stats)
        issue_collection = await IssueCollector(
            graphql,
            rate_limit_reserve=rate_limit_reserve,
        ).collect(
            settings.organization,
            repository_names,
            settings.username,
            refresh=refresh,
            organization_wide=repository_scope.all_repositories,
        )
        stats.merge(issue_collection.stats)
        review_collection = await ReviewCollector(
            graphql,
            rate_limit_reserve=rate_limit_reserve,
        ).collect(
            settings.organization,
            repository_names,
            settings.username,
            refresh=refresh,
            organization_wide=repository_scope.all_repositories,
        )
        stats.merge(review_collection.stats)
        if repository_scope.all_repositories:
            commit_presence = await CommitPresenceCollector(
                graphql,
                rate_limit_reserve=rate_limit_reserve,
            ).collect(
                settings.organization,
                repository_names,
                identities.emails,
                refresh=refresh,
            )
            stats.merge(commit_presence.stats)
            contributed_repositories = _contributed_repository_names(
                pull_request_collection.pull_requests,
                issue_collection.issues,
                review_collection.reviews,
                commit_presence.repositories,
            )

    git_repositories = tuple(
        repository.name_with_owner
        for repository in context.discovery.repositories
        if contributed_repositories is None
        or repository.name_with_owner in contributed_repositories
    )
    if git_scope_observer is not None:
        git_scope_observer(len(context.discovery.repositories), len(git_repositories))
    git_collection = collect_git_contributions(
        git_repositories,
        cache_directory=settings.cache_directory,
        token=settings.github_token,
        identities=identities,
        refresh=refresh,
        concurrency=git_concurrency,
    )
    report_repositories = tuple(
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
    )

    generated_at = datetime.now(UTC)
    report = CareerReport(
        organization=settings.organization,
        identity=ReportIdentity(
            username=settings.username,
            authenticated_as=context.authenticated_user.login,
        ),
        collection=CollectionMetadata(
            generated_at=generated_at,
            repository_scope_file=repository_scope.source_label,
            repository_count=len(context.discovery.repositories),
            github_api_requests=stats.api_requests,
            github_cache_hits=stats.cache_hits,
            git_repositories_processed=git_collection.repositories_processed,
            git_repositories_failed=git_collection.repositories_failed,
            graphql_rate_limit_remaining=(
                stats.latest_rate_limit.remaining if stats.latest_rate_limit else None
            ),
            graphql_rate_limit_reset_at=(
                stats.latest_rate_limit.reset_at if stats.latest_rate_limit else None
            ),
            warnings=tuple((*stats.warnings, *git_collection.warnings)),
        ),
        repositories=report_repositories,
        repository_analytics=summarize_repositories(
            report_repositories,
            git_collection.repository_analyses,
            pull_request_collection.pull_requests,
            review_collection.reviews,
            issue_collection.issues,
        ),
        language_summary=summarize_languages(
            report_repositories,
            git_collection.repository_analyses,
        ),
        timeline=build_timeline(
            git_collection.commits,
            pull_request_collection.pull_requests,
            review_collection.reviews,
            issue_collection.issues,
        ),
        commit_summary=summarize_commits(git_collection.commits),
        pull_request_summary=summarize_pull_requests(
            pull_request_collection.pull_requests,
            as_of=generated_at,
        ),
        review_summary=summarize_reviews(review_collection.reviews),
        issue_summary=summarize_issues(issue_collection.issues),
        pull_requests=pull_request_collection.pull_requests,
        reviews=review_collection.reviews,
        commits=git_collection.commits,
        issues=issue_collection.issues,
    )
    path = write_json_report(report, settings.output_directory)
    chart_paths = write_chart_bundle(report, settings.output_directory / "charts")
    html_path = write_html_report(report, settings.output_directory)
    markdown_path = write_markdown_report(report, settings.output_directory)
    csv_path = write_csv_report(report, settings.output_directory)
    return GeneratedCareerReport(
        report=report,
        path=path,
        discovery_context=context,
        chart_paths=chart_paths,
        html_path=html_path,
        markdown_path=markdown_path,
        csv_path=csv_path,
    )


def _discovery_stats(context: DiscoveryContext) -> CollectionStats:
    discovery = context.discovery
    stats = CollectionStats(
        api_requests=discovery.api_requests + 1,
        cache_hits=discovery.cache_hits,
    )
    if not discovery.from_cache:
        stats.latest_rate_limit = discovery.rate_limit
    return stats


def _contributed_repository_names(
    pull_requests: tuple[PullRequest, ...],
    issues: tuple[Issue, ...],
    reviews: tuple[PullRequestReview, ...],
    commit_repositories: frozenset[str],
) -> frozenset[str]:
    return frozenset(
        {
            *(item.repository for item in pull_requests),
            *(item.repository for item in issues),
            *(item.repository for item in reviews),
            *commit_repositories,
        }
    )
