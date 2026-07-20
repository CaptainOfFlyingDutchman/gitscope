"""Small, auditable wrapper around the native Git executable."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path


class GitCommandError(RuntimeError):
    """Raised when a native Git operation fails."""


def run_git(
    arguments: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    """Run Git without a shell and return stdout, using a concise safe failure message."""
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise GitCommandError("Git is not installed or is not available on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip().splitlines()
        reason = detail[-1] if detail else "Git command failed"
        raise GitCommandError(reason) from exc
    return completed.stdout
