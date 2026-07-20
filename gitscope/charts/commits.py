"""Commit timing-pattern charts."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from gitscope.charts.style import COMMITS_COLOR, apply_chart_style
from gitscope.models.report import CommitSummary

_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def commit_patterns_chart(summary: CommitSummary) -> go.Figure:
    """Compare authored commits by weekday and author-local hour."""
    hours = tuple(f"{hour:02d}" for hour in range(24))
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("By weekday", "By hour"),
        horizontal_spacing=0.12,
    )
    figure.add_trace(
        go.Bar(
            x=list(_WEEKDAYS),
            y=[summary.by_weekday.get(day, 0) for day in _WEEKDAYS],
            marker_color=COMMITS_COLOR,
            name="Commits",
            hovertemplate="%{x}: %{y:,}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Bar(
            x=list(hours),
            y=[summary.by_hour.get(hour, 0) for hour in hours],
            marker_color=COMMITS_COLOR,
            name="Commits",
            showlegend=False,
            hovertemplate="%{x}:00 — %{y:,} commits<extra></extra>",
        ),
        row=1,
        col=2,
    )
    apply_chart_style(figure, title="Commit Activity Patterns", height=480, show_legend=False)
    figure.update_xaxes(tickangle=-45, row=1, col=1)
    figure.update_xaxes(title_text="Author-local hour", dtick=2, row=1, col=2)
    figure.update_yaxes(title_text="Commits", rangemode="tozero", row=1, col=1)
    figure.update_yaxes(title_text="Commits", rangemode="tozero", row=1, col=2)
    return figure
