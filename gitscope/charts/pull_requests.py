"""Pull-request scale, lifecycle, and repository activity charts."""

from __future__ import annotations

import plotly.graph_objects as go

from gitscope.charts.style import PULL_REQUESTS_COLOR, apply_chart_style
from gitscope.models.pull_request import PullRequest
from gitscope.models.report import PullRequestSummary

_MERGE_TIME_BUCKETS = (
    ("< 1 day", 24),
    ("1-3 days", 72),
    ("3-7 days", 168),
    ("1-2 weeks", 336),
    ("2-4 weeks", 672),
    ("4+ weeks", float("inf")),
)


def pull_request_merge_times_chart(pull_requests: tuple[PullRequest, ...]) -> go.Figure:
    """Build a distribution of elapsed time for merged pull requests."""
    counts = dict.fromkeys((label for label, _ in _MERGE_TIME_BUCKETS), 0)
    for pull_request in pull_requests:
        if pull_request.merged_at is None:
            continue
        hours = max(
            0.0,
            (pull_request.merged_at - pull_request.created_at).total_seconds() / 3600,
        )
        for label, upper_bound in _MERGE_TIME_BUCKETS:
            if hours < upper_bound:
                counts[label] += 1
                break

    figure = go.Figure(
        go.Bar(
            x=list(counts),
            y=list(counts.values()),
            marker_color=PULL_REQUESTS_COLOR,
            text=[f"{value:,}" for value in counts.values()],
            textposition="auto",
            hovertemplate="%{x}: %{y:,} merged PRs<extra></extra>",
        )
    )
    apply_chart_style(figure, title="Pull Request Merge Times", show_legend=False)
    figure.update_xaxes(title_text="Time from creation to merge", type="category")
    figure.update_yaxes(title_text="Merged pull requests", rangemode="tozero")
    return figure


def pull_request_repository_activity_chart(summary: PullRequestSummary) -> go.Figure:
    """Rank repositories by authored pull-request count."""
    ranked = sorted(
        summary.by_repository.items(),
        key=lambda item: (item[1], item[0].casefold()),
    )[-12:]
    repositories = [repository for repository, _ in ranked]
    counts = [count for _, count in ranked]
    figure = go.Figure(
        go.Bar(
            x=counts,
            y=repositories,
            orientation="h",
            marker_color=PULL_REQUESTS_COLOR,
            text=[f"{value:,}" for value in counts],
            textposition="auto",
            hovertemplate="%{y}: %{x:,} PRs<extra></extra>",
        )
    )
    apply_chart_style(
        figure,
        title="Pull Requests by Repository",
        height=max(440, 90 + 32 * len(ranked)),
        show_legend=False,
    )
    figure.update_xaxes(title_text="Authored pull requests", rangemode="tozero")
    figure.update_yaxes(title_text="")
    return figure
