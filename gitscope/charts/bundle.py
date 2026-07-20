"""Secure standalone HTML export for the GitScope chart bundle."""

from __future__ import annotations

import os
from pathlib import Path

import plotly.io as pio
from plotly.graph_objects import Figure
from plotly.offline import get_plotlyjs

from gitscope.charts.activity import (
    monthly_activity_chart,
    pull_request_states_chart,
    yearly_activity_chart,
)
from gitscope.charts.commits import commit_patterns_chart
from gitscope.charts.issues import issue_states_chart
from gitscope.charts.languages import contributed_languages_chart, file_extensions_chart
from gitscope.charts.pull_requests import (
    pull_request_merge_times_chart,
    pull_request_repository_activity_chart,
)
from gitscope.charts.repositories import repository_rankings_chart
from gitscope.charts.reviews import review_activity_chart, review_states_chart
from gitscope.charts.timeline import career_milestones_chart
from gitscope.models.report import CareerReport

_PLOTLY_SCRIPT = "plotly.min.js"


def write_chart_bundle(report: CareerReport, output_directory: Path) -> tuple[Path, ...]:
    """Write private, offline, standalone chart pages with one shared Plotly runtime."""
    output_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output_directory, 0o700)
    _write_private_text(output_directory / _PLOTLY_SCRIPT, get_plotlyjs())

    paths: list[Path] = []
    for slug, figure in build_chart_figures(report):
        path = output_directory / f"{slug}.html"
        html = pio.to_html(
            figure,
            include_plotlyjs=False,
            full_html=True,
            div_id=f"gitscope-{slug}",
            config={
                "displaylogo": False,
                "responsive": True,
                "scrollZoom": False,
            },
        )
        html = html.replace(
            "</head>",
            f'<script charset="utf-8" src="{_PLOTLY_SCRIPT}"></script></head>',
            1,
        )
        _write_private_text(path, html)
        paths.append(path)
    return tuple(paths)


def build_chart_figures(report: CareerReport) -> tuple[tuple[str, Figure], ...]:
    """Build the complete, ordered set of report figures."""
    return (
        ("monthly-activity", monthly_activity_chart(report.timeline)),
        ("yearly-activity", yearly_activity_chart(report.timeline)),
        ("commit-patterns", commit_patterns_chart(report.commit_summary)),
        ("repository-rankings", repository_rankings_chart(report.repository_analytics)),
        ("pull-request-merge-times", pull_request_merge_times_chart(report.pull_requests)),
        (
            "pull-request-repositories",
            pull_request_repository_activity_chart(report.pull_request_summary),
        ),
        ("pull-request-states", pull_request_states_chart(report.pull_request_summary)),
        ("issue-states", issue_states_chart(report.issue_summary)),
        ("review-activity", review_activity_chart(report.timeline)),
        ("review-states", review_states_chart(report.review_summary)),
        ("contributed-languages", contributed_languages_chart(report.language_summary)),
        ("file-extensions", file_extensions_chart(report.language_summary)),
        ("career-milestones", career_milestones_chart(report.timeline)),
    )


def _write_private_text(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)
