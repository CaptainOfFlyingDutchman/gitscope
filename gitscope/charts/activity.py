"""Contribution activity and pull-request lifecycle charts."""

from __future__ import annotations

import plotly.graph_objects as go

from gitscope.charts.style import (
    COMMITS_COLOR,
    ISSUES_COLOR,
    PULL_REQUESTS_COLOR,
    REVIEWS_COLOR,
    apply_chart_style,
)
from gitscope.models.report import PullRequestSummary, TimelineSummary


def monthly_activity_chart(timeline: TimelineSummary) -> go.Figure:
    """Build a continuous stacked monthly contribution timeline."""
    periods = [period.period for period in timeline.monthly_activity]
    figure = go.Figure()
    for name, values, color in (
        ("Commits", [period.commits for period in timeline.monthly_activity], COMMITS_COLOR),
        (
            "Pull requests",
            [period.pull_requests for period in timeline.monthly_activity],
            PULL_REQUESTS_COLOR,
        ),
        ("Reviews", [period.reviews for period in timeline.monthly_activity], REVIEWS_COLOR),
        ("Issues", [period.issues for period in timeline.monthly_activity], ISSUES_COLOR),
    ):
        figure.add_trace(
            go.Scatter(
                x=periods,
                y=values,
                name=name,
                mode="lines",
                stackgroup="activity",
                line={"width": 1.5, "color": color},
                hovertemplate=f"{name}: %{{y:,}}<extra></extra>",
            )
        )
    apply_chart_style(figure, title="Monthly Contribution Activity", height=480)
    figure.update_xaxes(title_text="Month", tickangle=-45, type="category")
    figure.update_yaxes(title_text="Activities", rangemode="tozero")
    return figure


def yearly_activity_chart(timeline: TimelineSummary) -> go.Figure:
    """Build a grouped yearly activity comparison."""
    periods = [period.period for period in timeline.yearly_activity]
    figure = go.Figure(
        data=[
            go.Bar(
                x=periods,
                y=[period.commits for period in timeline.yearly_activity],
                name="Commits",
                marker_color=COMMITS_COLOR,
                hovertemplate="Commits: %{y:,}<extra></extra>",
            ),
            go.Bar(
                x=periods,
                y=[period.pull_requests for period in timeline.yearly_activity],
                name="Pull requests",
                marker_color=PULL_REQUESTS_COLOR,
                hovertemplate="Pull requests: %{y:,}<extra></extra>",
            ),
            go.Bar(
                x=periods,
                y=[period.reviews for period in timeline.yearly_activity],
                name="Reviews",
                marker_color=REVIEWS_COLOR,
                hovertemplate="Reviews: %{y:,}<extra></extra>",
            ),
            go.Bar(
                x=periods,
                y=[period.issues for period in timeline.yearly_activity],
                name="Issues",
                marker_color=ISSUES_COLOR,
                hovertemplate="Issues: %{y:,}<extra></extra>",
            ),
        ]
    )
    apply_chart_style(figure, title="Yearly Contribution Activity")
    figure.update_layout(barmode="group")
    figure.update_xaxes(title_text="Year", type="category")
    figure.update_yaxes(title_text="Activities", rangemode="tozero")
    return figure


def pull_request_states_chart(summary: PullRequestSummary) -> go.Figure:
    """Build a mutually exclusive pull-request lifecycle distribution."""
    labels = ["Merged", "Open", "Closed"]
    values = [summary.merged, summary.open, summary.closed]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=[COMMITS_COLOR, PULL_REQUESTS_COLOR, "#CC79A7"],
            text=[f"{value:,}" for value in values],
            textposition="auto",
            hovertemplate="%{y}: %{x:,}<extra></extra>",
        )
    )
    apply_chart_style(figure, title="Pull Request Outcomes", show_legend=False)
    figure.update_xaxes(title_text="Pull requests", rangemode="tozero")
    figure.update_yaxes(title_text="", categoryorder="array", categoryarray=labels[::-1])
    figure.add_annotation(
        text=f"Draft PRs: {summary.drafts:,} (included in lifecycle totals)",
        x=1,
        y=-0.2,
        xref="paper",
        yref="paper",
        xanchor="right",
        showarrow=False,
        font={"size": 11},
    )
    return figure
