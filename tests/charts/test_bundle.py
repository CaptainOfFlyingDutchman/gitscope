"""Tests for secure offline chart bundle export."""

import stat
from pathlib import Path

from gitscope.charts.bundle import write_chart_bundle
from tests.report.test_json import empty_report


def test_write_chart_bundle_creates_private_offline_pages(tmp_path: Path) -> None:
    output_directory = tmp_path / "charts"

    paths = write_chart_bundle(empty_report(), output_directory)

    assert len(paths) == 10
    assert all(path.exists() for path in paths)
    assert stat.S_IMODE(output_directory.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in paths)
    assert (output_directory / "plotly.min.js").exists()
    assert stat.S_IMODE((output_directory / "plotly.min.js").stat().st_mode) == 0o600
    assert 'src="plotly.min.js"' in paths[0].read_text(encoding="utf-8")
