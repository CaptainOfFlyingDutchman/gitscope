"""Create a deterministic SHA-256 manifest for release artifacts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def create_checksums(artifacts: tuple[Path, ...], output: Path) -> None:
    """Write sorted SHA-256 entries for non-empty, uniquely named artifacts."""
    if not artifacts:
        raise ValueError("At least one release artifact is required")
    names = [artifact.name for artifact in artifacts]
    if len(names) != len(set(names)):
        raise ValueError("Release artifact filenames must be unique")
    if output.resolve() in {artifact.resolve() for artifact in artifacts}:
        raise ValueError("Checksum output cannot also be an input artifact")

    entries: list[str] = []
    for artifact in sorted(artifacts, key=lambda path: path.name):
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise ValueError(f"Release artifact is missing or empty: {artifact}")
        digest = hashlib.sha256()
        with artifact.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        entries.append(f"{digest.hexdigest()}  {artifact.name}\n")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(entries), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        create_checksums(tuple(args.artifacts), args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Wrote SHA-256 manifest: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
