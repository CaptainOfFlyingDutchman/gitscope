"""Commit contribution aggregation."""

from __future__ import annotations

from collections import Counter

from gitscope.models.commit import CommitContribution
from gitscope.models.report import CommitSummary


def summarize_commits(commits: tuple[CommitContribution, ...]) -> CommitSummary:
    """Compute report-level commit and code-change totals."""
    repositories = Counter(commit.repository for commit in commits)
    years = Counter(str(commit.authored_at.year) for commit in commits)
    months = Counter(commit.authored_at.strftime("%Y-%m") for commit in commits)
    weekdays = Counter(commit.authored_at.strftime("%A") for commit in commits)
    hours = Counter(f"{commit.authored_at.hour:02d}" for commit in commits)
    return CommitSummary(
        total=len(commits),
        additions=sum(commit.additions for commit in commits),
        deletions=sum(commit.deletions for commit in commits),
        files_changed=sum(commit.files_changed for commit in commits),
        merge_commits=sum(commit.is_merge for commit in commits),
        first_contribution=commits[0].authored_at if commits else None,
        last_contribution=commits[-1].authored_at if commits else None,
        by_repository=dict(sorted(repositories.items())),
        by_year=dict(sorted(years.items())),
        by_month=dict(sorted(months.items())),
        by_weekday=dict(sorted(weekdays.items())),
        by_hour=dict(sorted(hours.items())),
    )
