"""Local, content-safe environment diagnostics for GitScope."""

from __future__ import annotations

import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from gitscope.cache import inspect_cache
from gitscope.report.export import ReportExportError, load_existing_report


class DiagnosticStatus(StrEnum):
    """Severity of one local diagnostic check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class DiagnosticCheck:
    """One sanitized diagnostic result."""

    name: str
    status: DiagnosticStatus
    detail: str


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    """Complete offline diagnostic result."""

    checks: tuple[DiagnosticCheck, ...]

    @property
    def has_failures(self) -> bool:
        return any(check.status is DiagnosticStatus.FAIL for check in self.checks)


def run_diagnostics(
    *,
    cache_directory: Path,
    report_path: Path,
    repositories_file: Path,
    log_file: Path,
    token_present: bool,
) -> DiagnosticReport:
    """Inspect local prerequisites and generated state without network access."""
    checks = [
        _python_check(),
        _git_check(),
        DiagnosticCheck(
            name="GitHub token",
            status=DiagnosticStatus.PASS if token_present else DiagnosticStatus.WARN,
            detail=(
                "Configured; value not displayed"
                if token_present
                else "Not configured; analyze requires it, offline commands do not"
            ),
        ),
        _cache_check(cache_directory),
        _log_check(log_file),
        _report_check(report_path),
        _repository_scope_check(repositories_file),
    ]
    return DiagnosticReport(checks=tuple(checks))


def _python_check() -> DiagnosticCheck:
    supported = sys.version_info >= (3, 13)
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return DiagnosticCheck(
        name="Python",
        status=DiagnosticStatus.PASS if supported else DiagnosticStatus.FAIL,
        detail=f"{version}; requires 3.13 or newer",
    )


def _git_check() -> DiagnosticCheck:
    executable = shutil.which("git")
    if executable is None:
        return DiagnosticCheck("Git", DiagnosticStatus.FAIL, "Not found on PATH")
    try:
        completed = subprocess.run(
            [executable, "--version"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError):
        return DiagnosticCheck("Git", DiagnosticStatus.FAIL, "Could not execute git --version")
    return DiagnosticCheck("Git", DiagnosticStatus.PASS, completed.stdout.strip())


def _cache_check(cache_directory: Path) -> DiagnosticCheck:
    inventory = inspect_cache(cache_directory)
    if not cache_directory.exists():
        return DiagnosticCheck(
            "Cache",
            DiagnosticStatus.WARN,
            "Not created yet; analyze will create it",
        )
    private = stat.S_IMODE(cache_directory.stat().st_mode) & 0o077 == 0
    status = DiagnosticStatus.PASS if private else DiagnosticStatus.WARN
    detail = (
        f"{inventory.graphql.entries} GraphQL entries, "
        f"{inventory.repositories.entries} repository mirrors, "
        f"{_format_bytes(inventory.size_bytes)}; "
        f"permissions {'private' if private else 'allow group or other access'}"
    )
    return DiagnosticCheck("Cache", status, detail)


def _report_check(report_path: Path) -> DiagnosticCheck:
    try:
        report = load_existing_report(report_path)
    except ReportExportError as exc:
        missing = not report_path.exists()
        return DiagnosticCheck(
            "Career report",
            DiagnosticStatus.WARN if missing else DiagnosticStatus.FAIL,
            "Not generated yet" if missing else str(exc),
        )
    return DiagnosticCheck(
        "Career report",
        DiagnosticStatus.PASS,
        f"Valid schema {report.schema_version}; {report.collection.repository_count} repositories",
    )


def _log_check(log_file: Path) -> DiagnosticCheck:
    if not log_file.exists():
        return DiagnosticCheck("Diagnostic log", DiagnosticStatus.WARN, "Not created yet")
    try:
        private = stat.S_IMODE(log_file.stat().st_mode) & 0o077 == 0
    except OSError:
        return DiagnosticCheck("Diagnostic log", DiagnosticStatus.FAIL, "Could not inspect file")
    return DiagnosticCheck(
        "Diagnostic log",
        DiagnosticStatus.PASS if private else DiagnosticStatus.WARN,
        f"{log_file}; permissions {'private' if private else 'allow group or other access'}",
    )


def _repository_scope_check(repositories_file: Path) -> DiagnosticCheck:
    try:
        lines = repositories_file.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return DiagnosticCheck("Repository scope", DiagnosticStatus.WARN, "File not found")
    except OSError:
        return DiagnosticCheck("Repository scope", DiagnosticStatus.FAIL, "File is not readable")
    entries = sum(bool(line.strip()) and not line.lstrip().startswith("#") for line in lines)
    return DiagnosticCheck(
        "Repository scope",
        DiagnosticStatus.PASS if entries else DiagnosticStatus.WARN,
        f"{entries} configured entries; names not displayed",
    )


def _format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"
