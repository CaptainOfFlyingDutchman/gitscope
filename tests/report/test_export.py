"""Tests for selective offline report regeneration."""

import stat
from pathlib import Path

import pytest

from gitscope.report.export import ReportExportError, export_existing_report
from tests.report.test_json import empty_report


def write_source_report(path: Path) -> None:
    path.write_text(empty_report().model_dump_json(), encoding="utf-8")


def test_html_export_writes_dashboard_support_without_standalone_charts(tmp_path: Path) -> None:
    report_path = tmp_path / "source" / "report.json"
    report_path.parent.mkdir()
    write_source_report(report_path)
    output_directory = tmp_path / "exported"

    exported = export_existing_report(
        report_path,
        output_directory,
        formats=("html",),
    )

    assert exported.formats == ("html",)
    assert exported.paths == (output_directory / "report.html",)
    assert (output_directory / "styles.css").exists()
    assert (output_directory / "theme.js").exists()
    assert (output_directory / "favicon.svg").exists()
    assert (output_directory / "charts" / "plotly.min.js").exists()
    assert not tuple((output_directory / "charts").glob("*.html"))
    assert stat.S_IMODE(output_directory.stat().st_mode) == 0o700


def test_all_export_regenerates_every_derived_output_once(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    write_source_report(report_path)
    output_directory = tmp_path / "exported"

    exported = export_existing_report(
        report_path,
        output_directory,
        formats=("charts", "html", "markdown", "csv", "html"),
    )

    assert exported.formats == ("charts", "html", "markdown", "csv")
    assert len(exported.paths) == 16
    assert len(tuple((output_directory / "charts").glob("*.html"))) == 13
    assert (output_directory / "report.html") in exported.paths
    assert (output_directory / "report.md") in exported.paths
    assert (output_directory / "report.csv") in exported.paths


@pytest.mark.parametrize("content", (None, "not-json"))
def test_export_rejects_missing_or_invalid_reports(tmp_path: Path, content: str | None) -> None:
    report_path = tmp_path / "report.json"
    if content is not None:
        report_path.write_text(content, encoding="utf-8")

    with pytest.raises(ReportExportError):
        export_existing_report(report_path, formats=("markdown",))
