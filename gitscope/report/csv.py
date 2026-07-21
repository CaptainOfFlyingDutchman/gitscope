"""Excel-friendly contribution activity CSV export."""

from __future__ import annotations

import csv
import os
from dataclasses import astuple, dataclass
from pathlib import Path

from gitscope.models.report import CareerReport

_HEADERS = (
    "schema_version",
    "organization",
    "username",
    "analysis_start",
    "analysis_end",
    "record_type",
    "occurred_at",
    "updated_at",
    "repository",
    "identifier",
    "pull_request_number",
    "issue_number",
    "title",
    "comment_count",
    "labels",
    "state",
    "url",
    "additions",
    "deletions",
    "files_changed",
    "commit_count",
    "is_merge",
    "is_draft",
)


@dataclass(frozen=True, slots=True)
class ActivityRow:
    """One normalized contribution event in the CSV ledger."""

    schema_version: str
    organization: str
    username: str
    analysis_start: str
    analysis_end: str
    record_type: str
    occurred_at: str
    updated_at: str
    repository: str
    identifier: str
    pull_request_number: str
    issue_number: str
    title: str
    comment_count: str
    labels: str
    state: str
    url: str
    additions: str
    deletions: str
    files_changed: str
    commit_count: str
    is_merge: str
    is_draft: str


def write_csv_report(report: CareerReport, output_directory: Path) -> Path:
    """Write a private UTF-8 CSV ledger with spreadsheet-safe text cells."""
    output_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output_directory, 0o700)
    path = output_directory / "report.csv"
    temporary = path.with_name(f".{path.name}.tmp")
    rows = sorted(
        _activity_rows(report),
        key=lambda row: (row.occurred_at, row.record_type, row.repository, row.identifier),
    )
    with temporary.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(_HEADERS)
        writer.writerows(tuple(_safe_cell(value) for value in astuple(row)) for row in rows)
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)
    return path


def _activity_rows(report: CareerReport) -> tuple[ActivityRow, ...]:
    shared = (
        report.schema_version,
        report.organization,
        report.identity.username,
        report.collection.analysis_start.isoformat() if report.collection.analysis_start else "",
        report.collection.analysis_end.isoformat() if report.collection.analysis_end else "",
    )
    commits = tuple(
        ActivityRow(
            *shared,
            record_type="commit",
            occurred_at=commit.authored_at.isoformat(),
            updated_at="",
            repository=commit.repository,
            identifier=commit.sha,
            pull_request_number="",
            issue_number="",
            title="",
            comment_count="",
            labels="",
            state="",
            url="",
            additions=str(commit.additions),
            deletions=str(commit.deletions),
            files_changed=str(commit.files_changed),
            commit_count="",
            is_merge=str(commit.is_merge).lower(),
            is_draft="",
        )
        for commit in report.commits
    )
    pull_requests = tuple(
        ActivityRow(
            *shared,
            record_type="pull_request",
            occurred_at=pull_request.created_at.isoformat(),
            updated_at=pull_request.updated_at.isoformat(),
            repository=pull_request.repository,
            identifier=pull_request.node_id,
            pull_request_number=str(pull_request.number),
            issue_number="",
            title=pull_request.title,
            comment_count="",
            labels="",
            state=pull_request.state.value,
            url=pull_request.url,
            additions=str(pull_request.additions),
            deletions=str(pull_request.deletions),
            files_changed=str(pull_request.changed_files),
            commit_count=str(pull_request.commit_count),
            is_merge="",
            is_draft=str(pull_request.is_draft).lower(),
        )
        for pull_request in report.pull_requests
    )
    reviews = tuple(
        ActivityRow(
            *shared,
            record_type="review",
            occurred_at=(review.submitted_at or review.created_at).isoformat(),
            updated_at="",
            repository=review.repository,
            identifier=review.node_id,
            pull_request_number=str(review.pull_request_number),
            issue_number="",
            title=review.pull_request_title,
            comment_count="",
            labels="",
            state=review.state.value,
            url=review.url,
            additions="",
            deletions="",
            files_changed="",
            commit_count="",
            is_merge="",
            is_draft="",
        )
        for review in report.reviews
    )
    issues = tuple(
        ActivityRow(
            *shared,
            record_type="issue",
            occurred_at=issue.created_at.isoformat(),
            updated_at=issue.updated_at.isoformat(),
            repository=issue.repository,
            identifier=issue.node_id,
            pull_request_number="",
            issue_number=str(issue.number),
            title=issue.title,
            comment_count=str(issue.comment_count),
            labels=", ".join(issue.labels),
            state=issue.state.value,
            url=issue.url,
            additions="",
            deletions="",
            files_changed="",
            commit_count="",
            is_merge="",
            is_draft="",
        )
        for issue in report.issues
    )
    return (*commits, *pull_requests, *issues, *reviews)


def _safe_cell(value: str) -> str:
    """Neutralize values Excel may otherwise interpret as formulas."""
    stripped = value.lstrip()
    if stripped.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value
