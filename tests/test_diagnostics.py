"""Tests for local GitScope diagnostics."""

from pathlib import Path

from gitscope.diagnostics import DiagnosticStatus, run_diagnostics
from tests.report.test_json import empty_report


def test_diagnostics_validate_local_state_without_exposing_names(tmp_path: Path) -> None:
    cache_directory = tmp_path / "cache"
    cache_directory.mkdir(mode=0o700)
    report_path = tmp_path / "report.json"
    report_path.write_text(empty_report().model_dump_json(), encoding="utf-8")
    repositories_file = tmp_path / "repositories"
    repositories_file.write_text("private-org/private-repo\n", encoding="utf-8")
    log_file = tmp_path / "logs" / "gitscope.log"
    log_file.parent.mkdir(mode=0o700)
    log_file.write_text("diagnostic", encoding="utf-8")
    log_file.chmod(0o600)

    report = run_diagnostics(
        cache_directory=cache_directory,
        report_path=report_path,
        repositories_file=repositories_file,
        log_file=log_file,
        token_present=False,
    )

    assert not report.has_failures
    assert any(
        check.name == "GitHub token" and check.status is DiagnosticStatus.WARN
        for check in report.checks
    )
    assert "private-org" not in " ".join(check.detail for check in report.checks)


def test_diagnostics_fail_for_invalid_existing_report(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text("invalid", encoding="utf-8")

    report = run_diagnostics(
        cache_directory=tmp_path / "cache",
        report_path=report_path,
        repositories_file=tmp_path / "missing-repositories",
        log_file=tmp_path / "missing.log",
        token_present=True,
    )

    assert report.has_failures
    assert any(
        check.name == "Career report" and check.status is DiagnosticStatus.FAIL
        for check in report.checks
    )
