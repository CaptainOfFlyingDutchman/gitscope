"""Path-free local Git statistics shared by collectors and analytics."""

from __future__ import annotations

from dataclasses import dataclass

from gitscope.models.commit import CommitContribution


@dataclass(frozen=True, slots=True)
class FileChangeAggregate:
    """Cumulative changes for one extension/language pair."""

    extension: str
    language: str
    additions: int
    deletions: int
    files_changed: int


@dataclass(frozen=True, slots=True)
class RepositoryCommitAnalysis:
    """Authored commits and safe file-change aggregates for one repository."""

    repository: str
    commits: tuple[CommitContribution, ...]
    file_changes: tuple[FileChangeAggregate, ...]
