"""Repository contribution ranking charts."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from gitscope.charts.style import (
    COMMITS_COLOR,
    PULL_REQUESTS_COLOR,
    REVIEWS_COLOR,
    apply_chart_style,
)
from gitscope.models.report import RepositoryContributionSummary


def repository_rankings_chart(
    repositories: tuple[RepositoryContributionSummary, ...],
    *,
    limit: int = 10,
) -> go.Figure:
    """Build aligned repository rankings on independent activity scales."""
    selected = tuple(repositories[:limit])
    labels = [item.name_with_owner.split("/", 1)[-1] for item in reversed(selected)]
    figure = make_subplots(
        rows=1,
        cols=3,
        shared_yaxes=True,
        subplot_titles=("Commits", "Pull requests", "Reviews"),
        horizontal_spacing=0.06,
    )
    for column, values, color, name in (
        (1, [item.commits for item in reversed(selected)], COMMITS_COLOR, "Commits"),
        (
            2,
            [item.pull_requests for item in reversed(selected)],
            PULL_REQUESTS_COLOR,
            "Pull requests",
        ),
        (3, [item.reviews for item in reversed(selected)], REVIEWS_COLOR, "Reviews"),
    ):
        figure.add_trace(
            go.Bar(
                x=values,
                y=labels,
                orientation="h",
                marker_color=color,
                name=name,
                text=[f"{value:,}" for value in values],
                textposition="auto",
                hovertemplate=f"%{{y}}<br>{name}: %{{x:,}}<extra></extra>",
                showlegend=False,
            ),
            row=1,
            col=column,
        )
        figure.update_xaxes(rangemode="tozero", row=1, col=column)
    apply_chart_style(
        figure,
        title=f"Repository Contribution Rankings — Top {len(selected)}",
        height=max(460, 88 + len(selected) * 42),
        show_legend=False,
    )
    figure.update_yaxes(title_text="Repository", row=1, col=1)
    return figure
