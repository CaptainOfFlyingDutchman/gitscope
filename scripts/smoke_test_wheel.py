"""Exercise the installed GitScope command from outside the source tree."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


def run_command(executable: Path, arguments: list[str], working_directory: Path) -> str:
    """Run one installed CLI command and return its combined diagnostic output."""
    environment = os.environ.copy()
    environment.pop("GITHUB_TOKEN", None)
    completed = subprocess.run(
        [str(executable), *arguments],
        cwd=working_directory,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = f"{completed.stdout}\n{completed.stderr}"
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(arguments)}\n{output}"
        )
    return output


def smoke_test(executable: Path, report_path: Path, expected_version: str) -> None:
    """Verify entry points, diagnostics, templates, charts, and offline outputs."""
    executable = executable.resolve()
    report_path = report_path.resolve()
    if not executable.is_file():
        raise ValueError(f"Installed executable not found: {executable}")
    if not report_path.is_file():
        raise ValueError(f"Smoke-test report not found: {report_path}")

    with tempfile.TemporaryDirectory(prefix="gitscope-wheel-") as temporary:
        working_directory = Path(temporary)
        version_output = run_command(executable, ["--version"], working_directory)
        if f"GitScope {expected_version}" not in version_output:
            raise RuntimeError("Installed command reported an unexpected version")

        help_output = run_command(executable, ["--help"], working_directory)
        for command in ("analyze", "cache", "doctor", "export", "resume"):
            if command not in help_output:
                raise RuntimeError(f"Installed help is missing the {command} command")

        run_command(
            executable,
            ["doctor", "--report", str(report_path)],
            working_directory,
        )

        report_output = working_directory / "report"
        run_command(
            executable,
            ["export", "all", "--report", str(report_path), "--output", str(report_output)],
            working_directory,
        )
        resume_output = working_directory / "resume"
        run_command(
            executable,
            [
                "resume",
                "--report",
                str(report_path),
                "--output",
                str(resume_output),
                "--name",
                "Example Engineer",
                "--title",
                "Staff Engineer",
                "--company",
                "Example Organization",
            ],
            working_directory,
        )

        required_outputs = {
            report_output / "report.html",
            report_output / "report.md",
            report_output / "report.csv",
            report_output / "charts" / "plotly.min.js",
            report_output / "charts" / "issue-states.html",
            report_output / "charts" / "pull-request-states.html",
            resume_output / "resume.md",
            resume_output / "resume.html",
            resume_output / "resume.css",
            resume_output / "resume.js",
        }
        missing = sorted(str(path) for path in required_outputs if not path.is_file())
        if missing:
            raise RuntimeError(f"Installed wheel did not generate: {', '.join(missing)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--expected-version")
    args = parser.parse_args()
    try:
        expected_version = args.expected_version or _project_version(Path("pyproject.toml"))
        smoke_test(args.executable, args.report, expected_version)
    except (OSError, RuntimeError, ValueError, KeyError, tomllib.TOMLDecodeError) as exc:
        print(f"Installed-wheel smoke test failed: {exc}", file=sys.stderr)
        return 1
    print("Installed-wheel smoke test passed")
    return 0


def _project_version(path: Path) -> str:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    version = payload["project"]["version"]
    if not isinstance(version, str):
        raise ValueError(f"Project version is not a string in {path}")
    return version


if __name__ == "__main__":
    raise SystemExit(main())
