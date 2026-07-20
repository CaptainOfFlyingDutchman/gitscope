"""Validate that a Git tag and release documentation match package metadata."""

from __future__ import annotations

import argparse
import ast
import re
import sys
import tomllib
from pathlib import Path

VERSION_TAG = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")


def validate_release(root: Path, tag: str) -> str:
    """Return the validated version or raise ValueError for an unsafe release."""
    if VERSION_TAG.fullmatch(tag) is None:
        raise ValueError(f"Release tag must use stable semantic versioning: {tag}")

    project_version = _project_version(root / "pyproject.toml")
    package_version = _package_version(root / "gitscope" / "__init__.py")
    expected_tag = f"v{project_version}"
    if tag != expected_tag:
        raise ValueError(f"Tag {tag} does not match project version {project_version}")
    if package_version != project_version:
        raise ValueError(
            f"Package version {package_version} does not match project version {project_version}"
        )

    release_notes = root / "docs" / "releases" / f"{tag}.md"
    if not release_notes.is_file() or not release_notes.read_text(encoding="utf-8").strip():
        raise ValueError(f"Release notes are missing or empty: {release_notes}")

    changelog = root / "CHANGELOG.md"
    if not changelog.is_file():
        raise ValueError("CHANGELOG.md is missing")
    changelog_heading = re.compile(
        rf"^## \[{re.escape(project_version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", re.M
    )
    if changelog_heading.search(changelog.read_text(encoding="utf-8")) is None:
        raise ValueError(f"CHANGELOG.md has no dated {project_version} release entry")
    return project_version


def _project_version(path: Path) -> str:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        version = payload["project"]["version"]
    except (FileNotFoundError, KeyError, OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"Could not read project version from {path}") from exc
    if not isinstance(version, str):
        raise ValueError(f"Project version is not a string in {path}")
    return version


def _package_version(path: Path) -> str:
    try:
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise ValueError(f"Could not read package version from {path}") from exc
    for statement in module.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if (
            isinstance(target, ast.Name)
            and target.id == "__version__"
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        ):
            return statement.value.value
    raise ValueError(f"Package __version__ is missing from {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    try:
        version = validate_release(args.root.resolve(), args.tag)
    except ValueError as exc:
        print(f"Release validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Validated GitScope release {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
