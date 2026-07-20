"""Polished, offline HTML dashboard generation."""

from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import plotly.io as pio
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from gitscope.charts.bundle import build_chart_figures
from gitscope.models.report import CareerReport

_TEMPLATE_DIRECTORY = Path(__file__).parent.parent / "templates"
_DASHBOARD_CHART_ORDER = (
    "monthly-activity",
    "yearly-activity",
    "file-extensions",
    "commit-patterns",
    "repository-rankings",
    "pull-request-merge-times",
    "pull-request-repositories",
    "pull-request-states",
    "issue-states",
    "review-activity",
    "review-states",
    "contributed-languages",
    "career-milestones",
)
_CHART_DESCRIPTIONS = {
    "monthly-activity": (
        "Monthly commits, pull requests, issues, and reviews across the selected scope."
    ),
    "yearly-activity": "Year-over-year comparison of contribution activity.",
    "commit-patterns": "Authored commit patterns by weekday and author-local hour.",
    "repository-rankings": "The repositories with the most commits, pull requests, and reviews.",
    "pull-request-merge-times": "How long merged pull requests remained open before merging.",
    "pull-request-repositories": "Repositories ranked by authored pull-request activity.",
    "pull-request-states": "Authored pull requests grouped by their current outcome.",
    "issue-states": "Authored issues grouped by their current lifecycle state.",
    "review-activity": "Submitted review activity over time.",
    "review-states": "Submitted reviews grouped by review state.",
    "contributed-languages": "Cumulative changed lines inferred from contributed file types.",
    "file-extensions": "Frequently changed file extensions, measured by cumulative file changes.",
    "career-milestones": "Notable first, last, and sequence-based career events.",
}


@dataclass(frozen=True, slots=True)
class DashboardChart:
    """A chart fragment and its accessible dashboard metadata."""

    slug: str
    description: str
    html: str


@dataclass(frozen=True, slots=True)
class HeatmapDay:
    """One calendar cell in the recent-activity heatmap."""

    value: int | None
    level: int
    label: str


@dataclass(frozen=True, slots=True)
class HeatmapMonth:
    """Month label positioned over a week column."""

    column: int
    label: str


@dataclass(frozen=True, slots=True)
class ContributionHeatmap:
    """A 53-week, Sunday-first activity calendar."""

    weeks: tuple[tuple[HeatmapDay, ...], ...]
    months: tuple[HeatmapMonth, ...]
    start: date
    end: date


def write_html_report(report: CareerReport, output_directory: Path) -> Path:
    """Render a private, offline dashboard and its companion stylesheet."""
    output_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output_directory, 0o700)

    environment = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIRECTORY),
        autoescape=select_autoescape(("html", "xml")),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters["number"] = lambda value: f"{value:,}"
    environment.filters["date"] = _format_date
    environment.filters["duration"] = _format_duration

    figures = dict(build_chart_figures(report))
    chart_slugs = tuple(
        slug
        for slug in _DASHBOARD_CHART_ORDER
        if slug != "issue-states" or report.issue_summary.total
    )
    charts = tuple(
        DashboardChart(
            slug=slug,
            description=_CHART_DESCRIPTIONS[slug],
            html=pio.to_html(
                figures[slug],
                include_plotlyjs=False,
                full_html=False,
                div_id=f"gitscope-dashboard-{slug}",
                config={"displaylogo": False, "responsive": True, "scrollZoom": False},
            ),
        )
        for slug in chart_slugs
    )
    repositories = tuple(
        sorted(
            report.repository_analytics,
            key=lambda item: (
                -(item.commits + item.pull_requests + item.issues + item.reviews),
                item.name_with_owner,
            ),
        )
    )
    recent_pull_requests = tuple(
        sorted(report.pull_requests, key=lambda item: item.updated_at, reverse=True)[:12]
    )
    recent_issues = tuple(
        sorted(report.issues, key=lambda item: item.updated_at, reverse=True)[:12]
    )
    template = environment.get_template("report.html")
    html = template.render(
        report=report,
        charts=charts,
        heatmap=build_contribution_heatmap(report),
        repositories=repositories,
        recent_pull_requests=recent_pull_requests,
        recent_issues=recent_issues,
    )

    stylesheet = (_TEMPLATE_DIRECTORY / "styles.css").read_text(encoding="utf-8")
    _write_private_text(output_directory / "styles.css", stylesheet)
    theme_script = (_TEMPLATE_DIRECTORY / "theme.js").read_text(encoding="utf-8")
    _write_private_text(output_directory / "theme.js", theme_script)
    path = output_directory / "report.html"
    _write_private_text(path, html)
    return path


def build_contribution_heatmap(report: CareerReport) -> ContributionHeatmap:
    """Aggregate commits, PRs, issues, and reviews into a recent activity calendar."""
    activity: Counter[date] = Counter(commit.authored_at.date() for commit in report.commits)
    activity.update(pull_request.created_at.date() for pull_request in report.pull_requests)
    activity.update((review.submitted_at or review.created_at).date() for review in report.reviews)
    activity.update(issue.created_at.date() for issue in report.issues)

    end = report.collection.generated_at.date()
    current_week_start = end - timedelta(days=(end.weekday() + 1) % 7)
    start = current_week_start - timedelta(weeks=52)
    positive = sorted(value for day, value in activity.items() if start <= day <= end and value)
    thresholds = (
        _percentile(positive, 0.25),
        _percentile(positive, 0.5),
        _percentile(positive, 0.75),
    )

    weeks: list[tuple[HeatmapDay, ...]] = []
    months: list[HeatmapMonth] = []
    previous_month: tuple[int, int] | None = None
    for week_index in range(53):
        week_start = start + timedelta(weeks=week_index)
        week: list[HeatmapDay] = []
        month_key = (week_start.year, week_start.month)
        if month_key != previous_month:
            months.append(HeatmapMonth(column=week_index + 1, label=week_start.strftime("%b")))
            previous_month = month_key
        for day_offset in range(7):
            day = week_start + timedelta(days=day_offset)
            if day > end:
                week.append(HeatmapDay(value=None, level=0, label="Outside report period"))
                continue
            value = activity[day]
            week.append(
                HeatmapDay(
                    value=value,
                    level=_heatmap_level(value, thresholds),
                    label=f"{day:%A, %B} {day.day}, {day:%Y}: {value:,} contributions",
                )
            )
        weeks.append(tuple(week))
    return ContributionHeatmap(weeks=tuple(weeks), months=tuple(months), start=start, end=end)


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    return values[round((len(values) - 1) * fraction)]


def _heatmap_level(value: int, thresholds: tuple[int, int, int]) -> int:
    if value == 0:
        return 0
    if value <= thresholds[0]:
        return 1
    if value <= thresholds[1]:
        return 2
    if value <= thresholds[2]:
        return 3
    return 4


def _format_date(value: date | datetime) -> str:
    formatted = value.strftime("%b")
    return f"{formatted} {value.day}, {value:%Y}"


def _format_duration(hours: float) -> str:
    if hours < 24:
        return f"{hours:.1f} hours"
    return f"{hours / 24:.1f} days"


def _write_private_text(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)
