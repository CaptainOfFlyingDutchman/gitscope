"""Lightweight, archive-friendly Markdown report generation."""

from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from gitscope.models.report import ActivityPeriod, CareerReport


def write_markdown_report(report: CareerReport, output_directory: Path) -> Path:
    """Write a private Markdown summary derived from the report contract."""
    output_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output_directory, 0o700)
    lines = _render_markdown(report)
    path = output_directory / "report.md"
    _write_private_text(path, "\n".join(lines).rstrip() + "\n")
    return path


def _render_markdown(report: CareerReport) -> list[str]:
    commits = report.commit_summary
    pull_requests = report.pull_request_summary
    reviews = report.review_summary
    issues = report.issue_summary
    timeline = report.timeline
    merge_rate = (
        f"{pull_requests.merge_rate * 100:.1f}%"
        if pull_requests.merge_rate is not None
        else "Not available"
    )
    lines = [
        f"# GitScope Career Report — {_escape_text(report.identity.username)}",
        "",
        (
            f"Engineering contribution report across **{report.collection.repository_count:,}** "
            f"repositories in **{_escape_text(report.organization)}**."
        ),
        "",
        (
            f"Generated {_format_date(report.collection.generated_at)} · "
            f"Schema {report.schema_version}"
        ),
        f"Analysis window (UTC): **{_analysis_window(report)}**",
        "",
        "[Open the interactive HTML dashboard](report.html)",
        "",
        "## Contribution overview",
        "",
    ]
    lines.extend(
        _table(
            ("Metric", "Value", "Context"),
            (
                ("Authored commits", f"{commits.total:,}", f"{commits.merge_commits:,} merges"),
                ("Authored pull requests", f"{pull_requests.total:,}", f"{merge_rate} merge rate"),
                ("Submitted reviews", f"{reviews.total:,}", f"{reviews.approvals:,} approvals"),
                (
                    "Authored issues",
                    f"{issues.total:,}",
                    (
                        f"{issues.closure_rate * 100:.1f}% closed"
                        if issues.closure_rate is not None
                        else "No issues collected"
                    ),
                ),
                (
                    "Active days",
                    f"{timeline.active_days:,}",
                    f"{timeline.career_span_days:,}-day contribution span",
                ),
                (
                    "Changed lines",
                    f"{commits.additions + commits.deletions:,}",
                    f"+{commits.additions:,} / -{commits.deletions:,}",
                ),
                ("Files changed", f"{commits.files_changed:,}", "Cumulative commit changes"),
            ),
        )
    )
    lines.extend(
        [
            "",
            "> Changed-line and file-change totals describe the collected work; they are not "
            "productivity metrics.",
            "",
            "## Contribution period",
            "",
            (f"- **First contribution:** {_format_optional_date(timeline.first_contribution)}"),
            f"- **Last contribution:** {_format_optional_date(timeline.last_contribution)}",
            f"- **Most active month:** {_activity_label(timeline.most_active_month)}",
            f"- **Most active year:** {_activity_label(timeline.most_active_year)}",
            "",
            "## Yearly activity",
            "",
        ]
    )
    lines.extend(
        _table(
            ("Year", "Commits", "Pull requests", "Issues", "Reviews", "Total"),
            tuple(
                (
                    period.period,
                    f"{period.commits:,}",
                    f"{period.pull_requests:,}",
                    f"{period.issues:,}",
                    f"{period.reviews:,}",
                    f"{period.total:,}",
                )
                for period in timeline.yearly_activity
            ),
            empty="No yearly activity was collected.",
        )
    )
    lines.extend(["", "## Repository contributions", ""])
    repositories = tuple(
        sorted(
            (
                item
                for item in report.repository_analytics
                if item.commits or item.pull_requests or item.issues or item.reviews
            ),
            key=lambda item: (
                -(item.commits + item.pull_requests + item.issues + item.reviews),
                item.name_with_owner,
            ),
        )
    )
    lines.extend(
        _table(
            (
                "Repository",
                "Language",
                "Commits",
                "PRs",
                "Issues",
                "Reviews",
                "Last contribution",
            ),
            tuple(
                (
                    repository.name_with_owner,
                    repository.primary_language or "—",
                    f"{repository.commits:,}",
                    f"{repository.pull_requests:,}",
                    f"{repository.issues:,}",
                    f"{repository.reviews:,}",
                    _format_optional_date(repository.last_contribution),
                )
                for repository in repositories
            ),
            empty="No repository activity was collected.",
        )
    )
    lines.extend(["", "## Contributed languages", ""])
    lines.extend(
        _table(
            ("Language", "Additions", "Deletions", "Files changed"),
            tuple(
                (
                    item.name,
                    f"{item.additions:,}",
                    f"{item.deletions:,}",
                    f"{item.files_changed:,}",
                )
                for item in report.language_summary.contributed_languages[:12]
            ),
            empty="No contributed-language changes were collected.",
        )
    )
    lines.extend(
        [
            "",
            "## Pull request outcomes",
            "",
            f"- **Merged:** {pull_requests.merged:,}",
            f"- **Open:** {pull_requests.open:,}",
            f"- **Closed without merge:** {pull_requests.closed:,}",
            f"- **Drafts:** {pull_requests.drafts:,}",
            "- **Average merge time:** "
            f"{_format_optional_duration(pull_requests.average_merge_time_hours)}",
            "- **Median merge time:** "
            f"{_format_optional_duration(pull_requests.median_merge_time_hours)}",
            "",
            "### Largest pull requests by changed lines",
            "",
        ]
    )
    lines.extend(
        _table(
            ("Pull request", "Repository", "State", "Changed lines", "Files"),
            tuple(
                (
                    f"[#{item.number}]({item.url}) {_escape_table_title(item.title)}",
                    f"{item.repository}#{item.number}",
                    item.state.value.title(),
                    f"{item.additions + item.deletions:,}",
                    f"{item.changed_files:,}",
                )
                for item in pull_requests.largest_by_changes
            ),
            empty="No authored pull requests were collected.",
        )
    )
    lines.extend(
        [
            "",
            "### Longest-running pull requests",
            "",
        ]
    )
    lines.extend(
        _table(
            ("Pull request", "Repository", "State", "Elapsed"),
            tuple(
                (
                    f"[#{item.number}]({item.url}) {_escape_table_title(item.title)}",
                    f"{item.repository}#{item.number}",
                    item.state.value.title(),
                    _format_duration(item.duration_hours),
                )
                for item in pull_requests.longest_running
            ),
            empty="No authored pull requests were collected.",
        )
    )
    lines.extend(
        [
            "",
            "## Issue outcomes",
            "",
            f"- **Closed:** {issues.closed:,}",
            f"- **Open:** {issues.open:,}",
            f"- **Comments:** {issues.total_comments:,}",
            "- **Average close time:** "
            f"{_format_optional_duration(issues.average_close_time_hours)}",
            f"- **Median close time:** {_format_optional_duration(issues.median_close_time_hours)}",
            "",
            "## Review outcomes",
            "",
            f"- **Approvals:** {reviews.approvals:,}",
            f"- **Changes requested:** {reviews.changes_requested:,}",
            f"- **Comments:** {reviews.comments:,}",
            f"- **Dismissed:** {reviews.dismissed:,}",
            "",
            "## Career milestones",
            "",
        ]
    )
    if timeline.milestones:
        lines.extend(
            f"- **{_format_date(item.occurred_at)}:** {_escape_text(item.label)} "
            f"— `{_escape_code(item.repository)}`"
            for item in timeline.milestones
        )
    else:
        lines.append("No career milestones were generated.")

    lines.extend(["", "## Recently updated pull requests", ""])
    recent_pull_requests = sorted(
        report.pull_requests,
        key=lambda item: item.updated_at,
        reverse=True,
    )[:12]
    if recent_pull_requests:
        lines.extend(
            f"- [{_escape_link_text(item.title)}]({item.url}) — "
            f"`{_escape_code(item.repository)}#{item.number}` · {item.state.value.title()} · "
            f"updated {_format_date(item.updated_at)}"
            for item in recent_pull_requests
        )
    else:
        lines.append("No authored pull requests were collected.")

    lines.extend(["", "## Recently updated issues", ""])
    recent_issues = sorted(report.issues, key=lambda item: item.updated_at, reverse=True)[:12]
    if recent_issues:
        lines.extend(
            f"- [{_escape_link_text(item.title)}]({item.url}) — "
            f"`{_escape_code(item.repository)}#{item.number}` · {item.state.value.title()} · "
            f"{item.comment_count:,} comments · updated {_format_date(item.updated_at)}"
            for item in recent_issues
        )
    else:
        lines.append("No authored issues were collected.")

    if report.collection.warnings:
        lines.extend(["", "## Collection notes", ""])
        lines.extend(f"- {_escape_text(warning)}" for warning in report.collection.warnings)

    lines.extend(
        [
            "",
            "---",
            "",
            (
                "Generated by GitScope · Data remains local to this report.  "
                "Made with care and ❤️ by "
                "[Manvendra Singh](https://www.manvendrask.com/about)."
            ),
        ]
    )
    return lines


def _table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    empty: str | None = None,
) -> list[str]:
    if not rows and empty is not None:
        return [empty]
    lines = [
        "| " + " | ".join(_escape_cell(header) for header in headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    lines.extend("| " + " | ".join(_escape_cell(value) for value in row) + " |" for row in rows)
    return lines


def _activity_label(period: ActivityPeriod | None) -> str:
    if period is None:
        return "Not available"
    return f"{period.period} ({period.total:,} activities)"


def _analysis_window(report: CareerReport) -> str:
    start = report.collection.analysis_start
    end = report.collection.analysis_end
    if start is not None and end is not None:
        return f"{_format_date(start)} through {_format_date(end)}"
    if start is not None:
        return f"{_format_date(start)} through present"
    if end is not None:
        return f"Beginning through {_format_date(end)}"
    return "Lifetime"


def _format_optional_date(value: date | datetime | None) -> str:
    return _format_date(value) if value is not None else "Not available"


def _format_optional_duration(value: float | None) -> str:
    return _format_duration(value) if value is not None else "Not available"


def _format_duration(hours: float) -> str:
    if hours < 24:
        return f"{hours:.1f} hours"
    return f"{hours / 24:.1f} days"


def _format_date(value: date | datetime) -> str:
    return f"{value:%b} {value.day}, {value:%Y}"


def _escape_cell(value: str) -> str:
    return _escape_text(value).replace("|", "\\|").replace("\n", "<br>")


def _escape_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("*", "\\*").replace("_", "\\_")


def _escape_link_text(value: str) -> str:
    return _escape_text(value).replace("[", "\\[").replace("]", "\\]")


def _escape_table_title(value: str) -> str:
    return value.replace("[", "&#91;").replace("]", "&#93;")


def _escape_code(value: str) -> str:
    return value.replace("`", "'")


def _write_private_text(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)
