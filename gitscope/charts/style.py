"""Shared, accessible Plotly presentation defaults."""

from __future__ import annotations

import plotly.graph_objects as go

COMMITS_COLOR = "#0072B2"
PULL_REQUESTS_COLOR = "#E69F00"
REVIEWS_COLOR = "#009E73"
ISSUES_COLOR = "#CC79A7"
ADDITIONS_COLOR = "#56B4E9"
DELETIONS_COLOR = "#D55E00"
NEUTRAL_COLOR = "#7A7A7A"
GRID_COLOR = "rgba(127, 127, 127, 0.22)"


def apply_chart_style(
    figure: go.Figure,
    *,
    title: str,
    height: int = 440,
    show_legend: bool = True,
) -> go.Figure:
    """Apply consistent typography, spacing, legend, and interaction defaults."""
    figure.update_layout(
        template="plotly_white",
        title={"text": title, "x": 0.01, "xanchor": "left"},
        height=height,
        margin={"l": 72, "r": 32, "t": 72, "b": 64},
        hovermode="x unified",
        showlegend=show_legend,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        font={"family": "Inter, system-ui, sans-serif", "size": 13},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    figure.update_xaxes(showgrid=False, zeroline=False, automargin=True)
    figure.update_yaxes(gridcolor=GRID_COLOR, zeroline=False, automargin=True)
    return figure
