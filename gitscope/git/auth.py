"""Token-safe non-interactive authentication for native Git."""

from __future__ import annotations

import os
import stat
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def git_auth_environment(token: str) -> Iterator[Mapping[str, str]]:
    """Yield an environment using askpass so the token never enters argv or a URL."""
    descriptor, raw_path = tempfile.mkstemp(prefix="gitscope-askpass-")
    path = Path(raw_path)
    try:
        script = (
            "#!/bin/sh\n"
            'case "$1" in\n'
            '  Username*) printf "%s\\n" "x-access-token" ;;\n'
            '  Password*) printf "%s\\n" "$GITSCOPE_GITHUB_TOKEN" ;;\n'
            "esac\n"
        )
        os.write(descriptor, script.encode())
        os.close(descriptor)
        descriptor = -1
        path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        yield {
            **os.environ,
            "GIT_ASKPASS": str(path),
            "GIT_TERMINAL_PROMPT": "0",
            "GITSCOPE_GITHUB_TOKEN": token,
        }
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        path.unlink(missing_ok=True)
