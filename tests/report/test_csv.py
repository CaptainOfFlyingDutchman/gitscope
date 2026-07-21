"""Tests for the Excel-friendly contribution CSV export."""

import csv
import stat
from datetime import UTC, datetime
from pathlib import Path

from gitscope.models.commit import CommitContribution
from gitscope.models.issue import Issue, IssueState
from gitscope.models.pull_request import PullRequest, PullRequestState
from gitscope.models.review import PullRequestReview, ReviewState
from gitscope.report.csv import write_csv_report
from tests.report.test_json import empty_report


def test_write_csv_report_normalizes_activity_and_neutralizes_formulas(tmp_path: Path) -> None:
    timestamp = datetime(2026, 7, 20, 12, tzinfo=UTC)
    commit = CommitContribution(
        sha="abc123",
        repository="josys-src/frontend",
        authored_at=timestamp,
        additions=10,
        deletions=2,
        files_changed=1,
        is_merge=False,
    )
    pull_request = PullRequest(
        node_id="PR_1",
        repository="josys-src/frontend",
        number=1,
        title='=HYPERLINK("https://malicious.example")',
        url="https://github.com/josys-src/frontend/pull/1",
        state=PullRequestState.MERGED,
        is_draft=False,
        created_at=timestamp,
        updated_at=timestamp,
        merged_at=timestamp,
        additions=20,
        deletions=4,
        changed_files=2,
        commit_count=2,
    )
    review = PullRequestReview(
        node_id="REVIEW_1",
        repository="josys-src/frontend",
        pull_request_number=2,
        pull_request_title="Review dashboard",
        pull_request_url="https://github.com/josys-src/frontend/pull/2",
        state=ReviewState.APPROVED,
        created_at=timestamp,
        submitted_at=timestamp,
        url="https://github.com/josys-src/frontend/pull/2#review-1",
    )
    issue = Issue(
        node_id="ISSUE_3",
        repository="josys-src/frontend",
        number=3,
        title="Report a problem",
        url="https://github.com/josys-src/frontend/issues/3",
        state=IssueState.OPEN,
        created_at=timestamp,
        updated_at=timestamp,
        comment_count=2,
        labels=("bug",),
    )
    report = empty_report().model_copy(
        update={
            "commits": (commit,),
            "pull_requests": (pull_request,),
            "reviews": (review,),
            "issues": (issue,),
        }
    )
    output_directory = tmp_path / "career-report"

    path = write_csv_report(report, output_directory)
    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert path == output_directory / "report.csv"
    assert stat.S_IMODE(output_directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [row["record_type"] for row in rows] == [
        "commit",
        "issue",
        "pull_request",
        "review",
    ]
    assert all(row["schema_version"] == "1.6" for row in rows)
    assert all(row["analysis_start"] == "" for row in rows)
    assert all(row["analysis_end"] == "" for row in rows)
    assert rows[0]["additions"] == "10"
    assert rows[0]["is_merge"] == "false"
    assert rows[1]["issue_number"] == "3"
    assert rows[1]["state"] == "OPEN"
    assert rows[1]["comment_count"] == "2"
    assert rows[1]["labels"] == "bug"
    assert rows[2]["title"].startswith("'=HYPERLINK")
    assert rows[2]["pull_request_number"] == "1"
    assert rows[2]["is_draft"] == "false"
    assert rows[3]["state"] == "APPROVED"
    assert rows[3]["pull_request_number"] == "2"
