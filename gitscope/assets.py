"""Packaged visual assets shared by portable GitScope outputs."""

from __future__ import annotations

import os
from pathlib import Path

_TEMPLATE_DIRECTORY = Path(__file__).parent / "templates"
FAVICON_FILENAME = "favicon.svg"


def write_favicon(output_directory: Path) -> Path:
    """Copy the packaged SVG favicon into an offline output directory."""
    output_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output_directory, 0o700)
    content = (_TEMPLATE_DIRECTORY / FAVICON_FILENAME).read_text(encoding="utf-8")
    path = output_directory / FAVICON_FILENAME
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)
    return path
