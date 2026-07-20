"""Efficient parsing of authored commits and numstat data."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from gitscope.git.identities import AuthorIdentities
from gitscope.git.languages import classify_file
from gitscope.git.runner import run_git
from gitscope.git.stats import FileChangeAggregate, RepositoryCommitAnalysis
from gitscope.models.commit import CommitContribution

_RECORD_SEPARATOR = "\x1e"
_FIELD_SEPARATOR = "\x1f"


def collect_repository_commits(
    repository: str,
    path: Path,
    identities: AuthorIdentities,
) -> tuple[CommitContribution, ...]:
    """Return target-authored commits from every cached ref in one Git traversal."""
    return analyze_repository_commits(repository, path, identities).commits


def analyze_repository_commits(
    repository: str,
    path: Path,
    identities: AuthorIdentities,
) -> RepositoryCommitAnalysis:
    """Return authored commits and path-free extension/language change totals."""
    output = run_git(
        [
            "log",
            "--all",
            "--use-mailmap",
            "--no-renames",
            f"--format={_RECORD_SEPARATOR}%H{_FIELD_SEPARATOR}%aI{_FIELD_SEPARATOR}%aN"
            f"{_FIELD_SEPARATOR}%aE{_FIELD_SEPARATOR}%P",
            "--numstat",
        ],
        cwd=path,
    )
    commits: list[CommitContribution] = []
    file_totals: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0])
    for raw_record in output.split(_RECORD_SEPARATOR):
        record = raw_record.lstrip("\n")
        if not record:
            continue
        header, _, stats = record.partition("\n")
        fields = header.split(_FIELD_SEPARATOR)
        if len(fields) != 5:
            continue
        sha, authored_at, author_name, author_email, parents = fields
        if not identities.matches(author_name, author_email):
            continue
        additions, deletions, file_changes = _parse_numstat(stats)
        for extension, language, added, deleted in file_changes:
            totals = file_totals[(extension, language)]
            totals[0] += added
            totals[1] += deleted
            totals[2] += 1
        commits.append(
            CommitContribution(
                sha=sha,
                repository=repository,
                authored_at=datetime.fromisoformat(authored_at),
                additions=additions,
                deletions=deletions,
                files_changed=len(file_changes),
                is_merge=len(parents.split()) > 1,
            )
        )
    aggregates = tuple(
        FileChangeAggregate(
            extension=extension,
            language=language,
            additions=totals[0],
            deletions=totals[1],
            files_changed=totals[2],
        )
        for (extension, language), totals in sorted(file_totals.items())
    )
    return RepositoryCommitAnalysis(
        repository=repository,
        commits=tuple(commits),
        file_changes=aggregates,
    )


def _parse_numstat(stats: str) -> tuple[int, int, tuple[tuple[str, str, int, int], ...]]:
    additions = deletions = 0
    changes: list[tuple[str, str, int, int]] = []
    for line in stats.splitlines():
        fields = line.split("\t", 2)
        if len(fields) != 3:
            continue
        added, deleted, path = fields
        added_count = int(added) if added.isdigit() else 0
        deleted_count = int(deleted) if deleted.isdigit() else 0
        extension, language = classify_file(path)
        additions += added_count
        deletions += deleted_count
        changes.append((extension, language, added_count, deleted_count))
    return additions, deletions, tuple(changes)
