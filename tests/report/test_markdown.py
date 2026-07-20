"""Tests for the lightweight Markdown report."""

import stat
from pathlib import Path

from gitscope.models.report import ReportIdentity
from gitscope.report.markdown import write_markdown_report
from tests.report.test_json import empty_report


def test_write_markdown_report_is_private_complete_and_portable(tmp_path: Path) -> None:
    output_directory = tmp_path / "career-report"
    report = empty_report().model_copy(
        update={
            "identity": ReportIdentity(username="octo_cat", authenticated_as="octocat"),
        }
    )

    path = write_markdown_report(report, output_directory)
    markdown = path.read_text(encoding="utf-8")

    assert path == output_directory / "report.md"
    assert stat.S_IMODE(output_directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert "# GitScope Career Report — octo\\_cat" in markdown
    assert "## Contribution overview" in markdown
    assert "## Repository contributions" in markdown
    assert "## Career milestones" in markdown
    assert "## Issue outcomes" in markdown
    assert "## Recently updated issues" in markdown
    assert "not productivity metrics" in markdown
    assert "[Open the interactive HTML dashboard](report.html)" in markdown
    assert "[Manvendra Singh](https://www.manvendrask.com/about)" in markdown
    assert markdown.endswith("\n")
