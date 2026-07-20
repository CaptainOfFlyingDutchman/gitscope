"""Efficient parsing of authored commits and numstat data."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from gitscope.git.identities import AuthorIdentities
from gitscope.git.runner import run_git
from gitscope.models.commit import CommitContribution

_RECORD_SEPARATOR = "\x1e"
_FIELD_SEPARATOR = "\x1f"


def collect_repository_commits(
    repository: str,
    path: Path,
    identities: AuthorIdentities,
) -> tuple[CommitContribution, ...]:
    """Return target-authored commits from every cached ref in one Git traversal."""
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
        additions, deletions, files_changed = _parse_numstat(stats)
        commits.append(
            CommitContribution(
                sha=sha,
                repository=repository,
                authored_at=datetime.fromisoformat(authored_at),
                additions=additions,
                deletions=deletions,
                files_changed=files_changed,
                is_merge=len(parents.split()) > 1,
            )
        )
    return tuple(commits)


def _parse_numstat(stats: str) -> tuple[int, int, int]:
    additions = deletions = files_changed = 0
    for line in stats.splitlines():
        fields = line.split("\t", 2)
        if len(fields) != 3:
            continue
        added, deleted, _path = fields
        additions += int(added) if added.isdigit() else 0
        deletions += int(deleted) if deleted.isdigit() else 0
        files_changed += 1
    return additions, deletions, files_changed
