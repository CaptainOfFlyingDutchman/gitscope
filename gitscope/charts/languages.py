"""Contribution-based language and extension charts."""

from __future__ import annotations

import plotly.graph_objects as go

from gitscope.charts.style import ADDITIONS_COLOR, COMMITS_COLOR, DELETIONS_COLOR, apply_chart_style
from gitscope.models.report import CodeChangeBreakdown, LanguageSummary


def contributed_languages_chart(summary: LanguageSummary, *, limit: int = 10) -> go.Figure:
    """Build a top-language cumulative change comparison."""
    selected = _top_by_churn(summary.contributed_languages, limit)
    labels = [item.name for item in reversed(selected)]
    figure = go.Figure(
        data=[
            go.Bar(
                x=[item.additions for item in reversed(selected)],
                y=labels,
                orientation="h",
                name="Additions",
                marker_color=ADDITIONS_COLOR,
                hovertemplate="%{y}<br>Additions: %{x:,}<extra></extra>",
            ),
            go.Bar(
                x=[item.deletions for item in reversed(selected)],
                y=labels,
                orientation="h",
                name="Deletions",
                marker_color=DELETIONS_COLOR,
                hovertemplate="%{y}<br>Deletions: %{x:,}<extra></extra>",
            ),
        ]
    )
    apply_chart_style(figure, title="Contributed Languages and File Types", height=520)
    figure.update_layout(barmode="stack")
    figure.update_xaxes(title_text="Cumulative changed lines", rangemode="tozero")
    figure.update_yaxes(title_text="Inferred category")
    return figure


def file_extensions_chart(summary: LanguageSummary, *, limit: int = 12) -> go.Figure:
    """Build a top-extension chart based on cumulative changed-file entries."""
    selected = tuple(
        sorted(summary.file_extensions, key=lambda item: (-item.files_changed, item.name))[:limit]
    )
    figure = go.Figure(
        go.Bar(
            x=[item.files_changed for item in reversed(selected)],
            y=[item.name for item in reversed(selected)],
            orientation="h",
            marker_color=COMMITS_COLOR,
            text=[f"{item.files_changed:,}" for item in reversed(selected)],
            textposition="auto",
            hovertemplate="%{y}: %{x:,} cumulative file changes<extra></extra>",
        )
    )
    apply_chart_style(figure, title="Most Frequently Changed File Extensions", height=540)
    figure.update_xaxes(title_text="Cumulative changed-file entries", rangemode="tozero")
    figure.update_yaxes(title_text="Extension")
    return figure


def _top_by_churn(
    items: tuple[CodeChangeBreakdown, ...],
    limit: int,
) -> tuple[CodeChangeBreakdown, ...]:
    return tuple(
        sorted(items, key=lambda item: (-(item.additions + item.deletions), item.name))[:limit]
    )
