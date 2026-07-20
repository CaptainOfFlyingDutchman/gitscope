"""Authored-issue lifecycle charts."""

from __future__ import annotations

import plotly.graph_objects as go

from gitscope.charts.style import ISSUES_COLOR, NEUTRAL_COLOR, apply_chart_style
from gitscope.models.report import IssueSummary


def issue_states_chart(summary: IssueSummary) -> go.Figure:
    """Build an authored-issue lifecycle distribution."""
    labels = ["Closed", "Open"]
    values = [summary.closed, summary.open]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=[ISSUES_COLOR, NEUTRAL_COLOR],
            text=[f"{value:,}" for value in values],
            textposition="auto",
            hovertemplate="%{y}: %{x:,}<extra></extra>",
        )
    )
    apply_chart_style(figure, title="Issue Outcomes", show_legend=False)
    figure.update_xaxes(title_text="Authored issues", rangemode="tozero")
    figure.update_yaxes(title_text="", categoryorder="array", categoryarray=labels[::-1])
    return figure
