"""Tests for commit aggregation."""

from datetime import UTC, datetime

from gitscope.analytics.commits import summarize_commits
from gitscope.models.commit import CommitContribution


def test_summarize_commits() -> None:
    first = CommitContribution(
        sha="a",
        repository="org/a",
        authored_at=datetime(2025, 1, 1, tzinfo=UTC),
        additions=5,
        deletions=2,
        files_changed=2,
        is_merge=False,
    )
    second = CommitContribution(
        sha="b",
        repository="org/b",
        authored_at=datetime(2026, 1, 1, tzinfo=UTC),
        additions=3,
        deletions=1,
        files_changed=1,
        is_merge=True,
    )

    summary = summarize_commits((first, second))

    assert summary.total == 2
    assert summary.additions == 8
    assert summary.deletions == 3
    assert summary.files_changed == 3
    assert summary.merge_commits == 1
    assert summary.by_repository == {"org/a": 1, "org/b": 1}
    assert summary.by_year == {"2025": 1, "2026": 1}
    assert summary.by_month == {"2025-01": 1, "2026-01": 1}
    assert summary.by_weekday == {"Thursday": 1, "Wednesday": 1}
    assert summary.by_hour == {"00": 2}
