"""Tests for the offline HTML dashboard."""

import stat
from datetime import UTC, datetime
from pathlib import Path

from gitscope.models.commit import CommitContribution
from gitscope.models.pull_request import PullRequest, PullRequestState
from gitscope.models.review import PullRequestReview, ReviewState
from gitscope.report.html import build_contribution_heatmap, write_html_report
from tests.report.test_json import empty_report


def test_heatmap_combines_commits_pull_requests_and_reviews() -> None:
    timestamp = datetime(2026, 7, 20, 12, tzinfo=UTC)
    commit = CommitContribution(
        sha="abc",
        repository="josys-src/frontend",
        authored_at=timestamp,
        additions=10,
        deletions=2,
        files_changed=1,
        is_merge=False,
    )
    pull_request = PullRequest(
        node_id="PR_1",
        repository="josys-src/frontend",
        number=1,
        title="Improve dashboard",
        url="https://github.com/josys-src/frontend/pull/1",
        state=PullRequestState.MERGED,
        is_draft=False,
        created_at=timestamp,
        updated_at=timestamp,
        merged_at=timestamp,
        additions=10,
        deletions=2,
        changed_files=1,
        commit_count=1,
    )
    review = PullRequestReview(
        node_id="REVIEW_1",
        repository="josys-src/frontend",
        pull_request_number=2,
        pull_request_title="Review dashboard",
        pull_request_url="https://github.com/josys-src/frontend/pull/2",
        state=ReviewState.APPROVED,
        created_at=timestamp,
        submitted_at=timestamp,
        url="https://github.com/josys-src/frontend/pull/2#review-1",
    )
    report = empty_report().model_copy(
        update={"commits": (commit,), "pull_requests": (pull_request,), "reviews": (review,)}
    )

    heatmap = build_contribution_heatmap(report)
    values = [day.value for week in heatmap.weeks for day in week]

    assert len(heatmap.weeks) == 53
    assert all(len(week) == 7 for week in heatmap.weeks)
    assert 3 in values
    assert heatmap.start <= timestamp.date() <= heatmap.end


def test_write_html_report_is_private_offline_and_escaped(tmp_path: Path) -> None:
    output_directory = tmp_path / "career-report"

    path = write_html_report(empty_report(), output_directory)
    html = path.read_text(encoding="utf-8")

    assert path == output_directory / "report.html"
    assert (output_directory / "styles.css").exists()
    assert (output_directory / "theme.js").exists()
    assert stat.S_IMODE(output_directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE((output_directory / "styles.css").stat().st_mode) == 0o600
    assert stat.S_IMODE((output_directory / "theme.js").stat().st_mode) == 0o600
    assert "Contribution overview" in html
    assert "Contribution heatmap" in html
    assert "Made with care and" in html
    assert "Manvendra Singh" in html
    assert 'href="https://www.manvendrask.com/about"' in html
    assert 'id="theme-toggle"' in html
    assert 'role="switch"' in html
    assert 'src="theme.js"' in html
    theme_script = (output_directory / "theme.js").read_text(encoding="utf-8")
    assert "prefers-color-scheme: dark" in theme_script
    assert "localStorage" in theme_script
    assert "Plotly.relayout" in theme_script
    assert "Repository Contribution Rankings" in html
    assert 'class="chart-card chart-card--wide"' in html
    commit_pattern_card = html.split('aria-label="Authored commit patterns', maxsplit=1)[0]
    assert commit_pattern_card.endswith('class="chart-card chart-card--wide" ')
    yearly_position = html.index("Yearly Contribution Activity")
    extensions_position = html.index("Most Frequently Changed File Extensions")
    commit_patterns_position = html.index("Commit Activity Patterns")
    assert yearly_position < extensions_position < commit_patterns_position
    assert 'src="charts/plotly.min.js"' in html
    assert "https://cdn.plot.ly" not in html
    assert html.count("plotly-graph-div") == 10
