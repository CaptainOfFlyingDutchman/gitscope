"""Atomic JSON report serialization."""

from __future__ import annotations

import os
from pathlib import Path

from gitscope.models.report import CareerReport


def write_json_report(report: CareerReport, output_directory: Path) -> Path:
    """Write report.json atomically with owner-only file permissions."""
    directory_created = not output_directory.exists()
    output_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory_created:
        os.chmod(output_directory, 0o700)

    destination = output_directory / "report.json"
    temporary = output_directory / ".report.json.tmp"
    temporary.write_text(f"{report.model_dump_json(indent=2)}\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(destination)
    os.chmod(destination, 0o600)
    return destination
