"""Repository and contribution-based language analytics."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable

from gitscope.git.stats import RepositoryCommitAnalysis
from gitscope.models.pull_request import PullRequest
from gitscope.models.report import (
    CodeChangeBreakdown,
    LanguageSummary,
    ReportRepository,
    RepositoryContributionSummary,
)
from gitscope.models.review import PullRequestReview


def summarize_repositories(
    repositories: tuple[ReportRepository, ...],
    analyses: tuple[RepositoryCommitAnalysis, ...],
    pull_requests: Iterable[PullRequest],
    reviews: Iterable[PullRequestReview],
) -> tuple[RepositoryContributionSummary, ...]:
    """Combine Git and GitHub activity into per-repository summaries."""
    analysis_by_repository = {analysis.repository: analysis for analysis in analyses}
    pull_request_counts = Counter(item.repository for item in pull_requests)
    review_counts = Counter(item.repository for item in reviews)
    summaries: list[RepositoryContributionSummary] = []
    for repository in repositories:
        analysis = analysis_by_repository.get(repository.name_with_owner)
        commits = analysis.commits if analysis else ()
        summaries.append(
            RepositoryContributionSummary(
                name_with_owner=repository.name_with_owner,
                primary_language=repository.primary_language,
                is_archived=repository.is_archived,
                commits=len(commits),
                pull_requests=pull_request_counts[repository.name_with_owner],
                reviews=review_counts[repository.name_with_owner],
                additions=sum(commit.additions for commit in commits),
                deletions=sum(commit.deletions for commit in commits),
                files_changed=sum(commit.files_changed for commit in commits),
                first_contribution=(
                    min(commit.authored_at for commit in commits) if commits else None
                ),
                last_contribution=(
                    max(commit.authored_at for commit in commits) if commits else None
                ),
            )
        )
    return tuple(
        sorted(
            summaries,
            key=lambda item: (
                -item.commits,
                -item.pull_requests,
                -item.reviews,
                item.name_with_owner,
            ),
        )
    )


def summarize_languages(
    repositories: tuple[ReportRepository, ...],
    analyses: tuple[RepositoryCommitAnalysis, ...],
) -> LanguageSummary:
    """Summarize declared primary languages and actual contributed file changes."""
    primary_languages = Counter(
        repository.primary_language
        for repository in repositories
        if repository.primary_language is not None
    )
    language_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    extension_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for analysis in analyses:
        for change in analysis.file_changes:
            _merge_totals(
                language_totals[change.language],
                change.additions,
                change.deletions,
                change.files_changed,
            )
            _merge_totals(
                extension_totals[change.extension],
                change.additions,
                change.deletions,
                change.files_changed,
            )
    return LanguageSummary(
        primary_repository_languages=dict(sorted(primary_languages.items())),
        contributed_languages=_breakdowns(language_totals),
        file_extensions=_breakdowns(extension_totals),
    )


def _merge_totals(target: list[int], additions: int, deletions: int, files_changed: int) -> None:
    target[0] += additions
    target[1] += deletions
    target[2] += files_changed


def _breakdowns(totals: dict[str, list[int]]) -> tuple[CodeChangeBreakdown, ...]:
    return tuple(
        CodeChangeBreakdown(
            name=name,
            additions=values[0],
            deletions=values[1],
            files_changed=values[2],
        )
        for name, values in sorted(
            totals.items(),
            key=lambda item: (-(item[1][0] + item[1][1]), item[0]),
        )
    )
