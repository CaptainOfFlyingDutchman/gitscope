"""Offline regeneration of report outputs from an existing JSON contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from gitscope.charts.bundle import write_chart_bundle, write_plotly_runtime
from gitscope.models.report import CareerReport
from gitscope.report.csv import write_csv_report
from gitscope.report.html import write_html_report
from gitscope.report.markdown import write_markdown_report

ExportFormat = Literal["html", "markdown", "csv", "charts"]


class ReportExportError(ValueError):
    """An existing report could not be read or exported safely."""


@dataclass(frozen=True, slots=True)
class OfflineExport:
    """Validated source report and the primary files regenerated from it."""

    report: CareerReport
    output_directory: Path
    formats: tuple[ExportFormat, ...]
    paths: tuple[Path, ...]


def export_existing_report(
    report_path: Path,
    output_directory: Path | None = None,
    *,
    formats: tuple[ExportFormat, ...],
) -> OfflineExport:
    """Regenerate selected outputs without making network or Git calls."""
    report = load_existing_report(report_path)
    destination = output_directory or report_path.parent
    normalized_formats = tuple(dict.fromkeys(formats))
    paths: list[Path] = []
    for output_format in normalized_formats:
        if output_format == "html":
            if "charts" not in normalized_formats:
                write_plotly_runtime(destination / "charts")
            paths.append(write_html_report(report, destination))
        elif output_format == "markdown":
            paths.append(write_markdown_report(report, destination))
        elif output_format == "csv":
            paths.append(write_csv_report(report, destination))
        else:
            paths.extend(write_chart_bundle(report, destination / "charts"))
    return OfflineExport(
        report=report,
        output_directory=destination,
        formats=normalized_formats,
        paths=tuple(paths),
    )


def load_existing_report(report_path: Path) -> CareerReport:
    """Read and validate an existing versioned GitScope report."""
    try:
        content = report_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReportExportError(f"Report file not found: {report_path}") from exc
    except OSError as exc:
        raise ReportExportError(f"Could not read report file: {report_path}") from exc
    try:
        return CareerReport.model_validate_json(content)
    except ValidationError as exc:
        raise ReportExportError(
            f"Report is not a supported GitScope JSON contract: {report_path}"
        ) from exc
