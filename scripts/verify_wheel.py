"""Validate the public contents and metadata of a GitScope wheel."""

from __future__ import annotations

import argparse
import sys
import tarfile
import tomllib
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

REQUIRED_MEMBERS = {
    "gitscope/__init__.py",
    "gitscope/assets.py",
    "gitscope/cli.py",
    "gitscope/py.typed",
    "gitscope/templates/favicon.svg",
    "gitscope/templates/report.html",
    "gitscope/templates/resume.css",
    "gitscope/templates/resume.html",
    "gitscope/templates/resume.js",
    "gitscope/templates/styles.css",
    "gitscope/templates/theme.js",
}
FORBIDDEN_PARTS = {
    ".env",
    ".gitscope",
    ".gitscope-identities",
    ".gitscope-repositories",
    "__pycache__",
    "career-report",
}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}
REQUIRED_SDIST_SUFFIXES = {
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "docs/architecture.md",
    "docs/installation.md",
    "docs/releasing.md",
    "pyproject.toml",
    "scripts/create_checksums.py",
    "scripts/smoke_test_wheel.py",
    "scripts/validate_release.py",
    "tests/fixtures/minimal-report.json",
}


def verify_wheel(wheel_path: Path, expected_version: str) -> None:
    """Raise ValueError when a wheel is incomplete or contains private state."""
    try:
        with ZipFile(wheel_path) as archive:
            members = set(archive.namelist())
            _verify_members(members)
            metadata_path = _single_member(members, ".dist-info/METADATA")
            entry_points_path = _single_member(members, ".dist-info/entry_points.txt")
            metadata = archive.read(metadata_path).decode("utf-8")
            entry_points = archive.read(entry_points_path).decode("utf-8")
    except (BadZipFile, OSError) as exc:
        raise ValueError(f"Could not inspect wheel: {wheel_path}") from exc

    required_metadata = ("Name: gitscope", f"Version: {expected_version}")
    missing_metadata = [item for item in required_metadata if item not in metadata]
    if missing_metadata:
        raise ValueError(f"Wheel metadata is missing: {', '.join(missing_metadata)}")
    if "gitscope = gitscope.cli:app" not in entry_points:
        raise ValueError("Wheel does not define the gitscope console entry point")


def verify_sdist(sdist_path: Path, expected_version: str) -> None:
    """Raise ValueError when the source archive is incomplete or unsafe."""
    try:
        with tarfile.open(sdist_path, mode="r:gz") as archive:
            members = {member.name for member in archive.getmembers() if member.isfile()}
    except (OSError, tarfile.TarError) as exc:
        raise ValueError(f"Could not inspect source distribution: {sdist_path}") from exc

    required_suffixes = REQUIRED_SDIST_SUFFIXES | {f"docs/releases/v{expected_version}.md"}
    missing = sorted(
        suffix
        for suffix in required_suffixes
        if not any(member.endswith(f"/{suffix}") for member in members)
    )
    if missing:
        raise ValueError(f"Source distribution is missing: {', '.join(missing)}")

    forbidden: list[str] = []
    for member in members:
        path = PurePosixPath(member)
        if FORBIDDEN_PARTS.intersection(path.parts) or path.suffix in FORBIDDEN_SUFFIXES:
            forbidden.append(member)
    if forbidden:
        names = ", ".join(sorted(forbidden))
        raise ValueError(f"Source distribution contains private or generated files: {names}")


def _verify_members(members: set[str]) -> None:
    missing = sorted(REQUIRED_MEMBERS - members)
    if missing:
        raise ValueError(f"Wheel is missing required files: {', '.join(missing)}")

    forbidden: list[str] = []
    for member in members:
        path = PurePosixPath(member)
        if FORBIDDEN_PARTS.intersection(path.parts) or path.suffix in FORBIDDEN_SUFFIXES:
            forbidden.append(member)
    if forbidden:
        names = ", ".join(sorted(forbidden))
        raise ValueError(f"Wheel contains private or generated files: {names}")


def _single_member(members: set[str], suffix: str) -> str:
    matching = sorted(member for member in members if member.endswith(suffix))
    if len(matching) != 1:
        raise ValueError(f"Expected exactly one *{suffix} file; found {len(matching)}")
    return matching[0]


def _project_version(path: Path) -> str:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        version = payload["project"]["version"]
    except (FileNotFoundError, KeyError, OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"Could not read project version from {path}") from exc
    if not isinstance(version, str):
        raise ValueError(f"Project version is not a string in {path}")
    return version


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--sdist", type=Path)
    parser.add_argument("--expected-version")
    args = parser.parse_args()
    try:
        expected_version = args.expected_version or _project_version(Path("pyproject.toml"))
        verify_wheel(args.wheel, expected_version)
        if args.sdist is not None:
            verify_sdist(args.sdist, expected_version)
    except ValueError as exc:
        print(f"Distribution verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"Verified wheel contents: {args.wheel}")
    if args.sdist is not None:
        print(f"Verified source distribution contents: {args.sdist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
