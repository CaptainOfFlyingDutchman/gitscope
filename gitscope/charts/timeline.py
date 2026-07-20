"""Career milestone timeline chart."""

from __future__ import annotations

import plotly.graph_objects as go

from gitscope.charts.style import COMMITS_COLOR, apply_chart_style
from gitscope.models.report import TimelineSummary


def career_milestones_chart(timeline: TimelineSummary) -> go.Figure:
    """Build a chronological milestone lane with alternating labels."""
    milestones = timeline.milestones
    levels = tuple((index % 3) - 1 for index in range(len(milestones)))
    figure = go.Figure(
        go.Scatter(
            x=[milestone.occurred_at for milestone in milestones],
            y=levels,
            mode="markers+text",
            marker={"size": 12, "color": COMMITS_COLOR, "line": {"width": 1, "color": "white"}},
            text=[milestone.label for milestone in milestones],
            textposition=["bottom center" if level < 0 else "top center" for level in levels],
            customdata=[milestone.repository for milestone in milestones],
            hovertemplate="%{text}<br>%{x|%Y-%m-%d}<br>%{customdata}<extra></extra>",
        )
    )
    if milestones:
        figure.add_shape(
            type="line",
            x0=milestones[0].occurred_at,
            x1=milestones[-1].occurred_at,
            y0=0,
            y1=0,
            line={"color": "rgba(127,127,127,0.5)", "width": 2},
            layer="below",
        )
    apply_chart_style(figure, title="Career Milestones", height=500, show_legend=False)
    figure.update_xaxes(title_text="Date")
    figure.update_yaxes(visible=False, range=[-1.8, 1.8])
    figure.update_layout(hovermode="closest")
    return figure
