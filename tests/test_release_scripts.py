from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.create_checksums import create_checksums
from scripts.validate_release import validate_release

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_current_release_metadata_is_consistent() -> None:
    assert validate_release(PROJECT_ROOT, "v0.1.0") == "0.1.0"


def test_release_tag_must_match_project_version() -> None:
    with pytest.raises(ValueError, match="does not match project version"):
        validate_release(PROJECT_ROOT, "v0.1.1")


def test_create_checksums_writes_sorted_sha256_manifest(tmp_path: Path) -> None:
    source = tmp_path / "gitscope-0.1.0.tar.gz"
    wheel = tmp_path / "gitscope-0.1.0-py3-none-any.whl"
    source.write_bytes(b"source distribution")
    wheel.write_bytes(b"wheel distribution")
    output = tmp_path / "SHA256SUMS"

    create_checksums((source, wheel), output)

    expected = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in sorted((source, wheel), key=lambda item: item.name)
    )
    assert output.read_text(encoding="utf-8") == expected


def test_create_checksums_rejects_empty_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "empty.whl"
    artifact.touch()

    with pytest.raises(ValueError, match="missing or empty"):
        create_checksums((artifact,), tmp_path / "SHA256SUMS")
