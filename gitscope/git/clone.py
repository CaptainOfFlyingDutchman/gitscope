"""Private, incremental repository mirrors for complete history statistics."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from gitscope.git.auth import git_auth_environment
from gitscope.git.runner import GitCommandError, run_git


@dataclass(frozen=True, slots=True)
class RepositoryCheckout:
    """A locally cached repository ready for history analysis."""

    name_with_owner: str
    path: Path


def prepare_repository(
    name_with_owner: str,
    cache_directory: Path,
    token: str,
    *,
    refresh: bool = False,
) -> RepositoryCheckout:
    """Clone or update a bare repository suitable for complete historical numstat."""
    owner, name = _split_repository(name_with_owner)
    root = cache_directory / "repositories" / owner
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(cache_directory / "repositories", 0o700)
    destination = root / f"{name}.git"
    remote_url = f"https://github.com/{owner}/{name}.git"

    with git_auth_environment(token) as env:
        if destination.exists():
            if not (destination / "HEAD").is_file():
                raise GitCommandError(f"cache path is not a bare Git repository: {destination}")
            origin = run_git(["remote", "get-url", "origin"], cwd=destination).strip()
            if origin.rstrip("/") != remote_url.rstrip("/"):
                raise GitCommandError(f"cached repository has an unexpected origin: {destination}")
            partial_clone = _is_partial_clone(destination)
            if refresh or partial_clone:
                filter_arguments = ["--refetch", "--no-filter"] if partial_clone else []
                run_git(
                    [
                        "fetch",
                        "--prune",
                        "--tags",
                        *filter_arguments,
                        "origin",
                        "+refs/heads/*:refs/heads/*",
                    ],
                    cwd=destination,
                    env=env,
                )
                if partial_clone:
                    _mark_full_clone(destination)
        else:
            run_git(
                ["clone", "--bare", remote_url, str(destination)],
                env=env,
            )
    return RepositoryCheckout(name_with_owner=name_with_owner, path=destination)


def _split_repository(name_with_owner: str) -> tuple[str, str]:
    owner, separator, name = name_with_owner.partition("/")
    if not separator or not owner or not name or "/" in name:
        raise GitCommandError(f"invalid repository name: {name_with_owner}")
    return owner, name


def _is_partial_clone(path: Path) -> bool:
    try:
        value = run_git(["config", "--get", "remote.origin.promisor"], cwd=path)
    except GitCommandError:
        return False
    return value.strip().casefold() == "true"


def _mark_full_clone(path: Path) -> None:
    """Remove partial-clone settings after a successful unfiltered refetch."""
    run_git(["config", "--unset", "remote.origin.promisor"], cwd=path)
    run_git(["config", "--unset", "remote.origin.partialclonefilter"], cwd=path)
