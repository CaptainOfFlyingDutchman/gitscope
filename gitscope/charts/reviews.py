"""Review activity and state charts."""

from __future__ import annotations

import plotly.graph_objects as go

from gitscope.charts.style import REVIEWS_COLOR, apply_chart_style
from gitscope.models.report import ReviewSummary, TimelineSummary


def review_activity_chart(timeline: TimelineSummary) -> go.Figure:
    """Build a monthly submitted-review trend."""
    figure = go.Figure(
        go.Scatter(
            x=[period.period for period in timeline.monthly_activity],
            y=[period.reviews for period in timeline.monthly_activity],
            mode="lines+markers",
            line={"color": REVIEWS_COLOR, "width": 2.5},
            marker={"size": 5},
            fill="tozeroy",
            fillcolor="rgba(0, 158, 115, 0.14)",
            hovertemplate="%{x}<br>Reviews: %{y:,}<extra></extra>",
        )
    )
    apply_chart_style(figure, title="Monthly Review Activity", show_legend=False)
    figure.update_xaxes(title_text="Month", tickangle=-45, type="category")
    figure.update_yaxes(title_text="Submitted reviews", rangemode="tozero")
    return figure


def review_states_chart(summary: ReviewSummary) -> go.Figure:
    """Build a complete submitted-review state distribution."""
    known_total = (
        summary.approvals + summary.changes_requested + summary.comments + summary.dismissed
    )
    labels = ["Approved", "Changes requested", "Commented", "Dismissed", "Pending/other"]
    values = [
        summary.approvals,
        summary.changes_requested,
        summary.comments,
        summary.dismissed,
        max(0, summary.total - known_total),
    ]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=[REVIEWS_COLOR, "#D55E00", "#56B4E9", "#CC79A7", "#7A7A7A"],
            text=[f"{value:,}" for value in values],
            textposition="auto",
            hovertemplate="%{y}: %{x:,}<extra></extra>",
        )
    )
    apply_chart_style(figure, title="Review Outcomes", show_legend=False)
    figure.update_xaxes(title_text="Submitted reviews", rangemode="tozero")
    figure.update_yaxes(title_text="", categoryorder="array", categoryarray=labels[::-1])
    return figure
