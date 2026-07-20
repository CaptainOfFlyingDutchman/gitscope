"""Concurrent, failure-isolated local Git contribution collection."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from gitscope.git.clone import prepare_repository
from gitscope.git.commits import collect_repository_commits
from gitscope.git.identities import AuthorIdentities
from gitscope.git.runner import GitCommandError
from gitscope.models.commit import CommitContribution


@dataclass(frozen=True, slots=True)
class GitCollection:
    """Collected commits plus repository-level completeness metadata."""

    commits: tuple[CommitContribution, ...]
    repositories_processed: int
    repositories_failed: int
    warnings: tuple[str, ...]


def collect_git_contributions(
    repositories: tuple[str, ...],
    *,
    cache_directory: Path,
    token: str,
    identities: AuthorIdentities,
    refresh: bool = False,
    concurrency: int = 4,
) -> GitCollection:
    """Prepare and inspect repositories concurrently without failing the whole report."""
    worker_count = max(1, min(concurrency, len(repositories)))
    commits: list[CommitContribution] = []
    warnings: list[str] = []
    processed = 0

    def inspect(repository: str) -> tuple[CommitContribution, ...]:
        checkout = prepare_repository(repository, cache_directory, token, refresh=refresh)
        return collect_repository_commits(repository, checkout.path, identities)

    if not repositories:
        return GitCollection((), 0, 0, ())
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="gitscope-git") as pool:
        futures = {pool.submit(inspect, repository): repository for repository in repositories}
        for future in as_completed(futures):
            repository = futures[future]
            try:
                commits.extend(future.result())
                processed += 1
            except (GitCommandError, OSError) as exc:
                warnings.append(f"Could not analyze {repository}: {exc}")

    commits.sort(key=lambda commit: (commit.authored_at, commit.repository, commit.sha))
    warnings.sort()
    return GitCollection(
        commits=tuple(commits),
        repositories_processed=processed,
        repositories_failed=len(repositories) - processed,
        warnings=tuple(warnings),
    )
