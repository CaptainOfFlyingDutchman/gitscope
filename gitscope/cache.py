"""Private on-disk JSON cache used by GitScope collectors."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class CacheTarget(StrEnum):
    """Regenerable cache sections that may be inspected or cleared."""

    GRAPHQL = "graphql"
    REPOSITORIES = "repositories"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class CacheSection:
    """Content-free metadata about one cache section."""

    name: str
    path: Path
    exists: bool
    entries: int
    size_bytes: int


@dataclass(frozen=True, slots=True)
class CacheInventory:
    """Safe aggregate metadata for the GitScope cache."""

    root: Path
    graphql: CacheSection
    repositories: CacheSection

    @property
    def size_bytes(self) -> int:
        return self.graphql.size_bytes + self.repositories.size_bytes


@dataclass(frozen=True, slots=True)
class CacheClearResult:
    """Metadata about cache content removed by an explicit request."""

    target: CacheTarget
    sections_removed: tuple[str, ...]
    bytes_reclaimed: int


class JsonCache:
    """Store JSON responses in an owner-only cache directory."""

    def __init__(self, directory: Path, *, ttl_seconds: int = 3600) -> None:
        self.directory = directory
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def key_for(namespace: str, payload: Mapping[str, Any]) -> str:
        """Create a stable opaque cache key without exposing request data in filenames."""
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(serialized.encode()).hexdigest()
        return f"{namespace}-{digest}"

    def get(self, key: str) -> dict[str, Any] | None:
        """Return a fresh cached object, ignoring missing or malformed entries."""
        path = self._path(key)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            stored_at = float(payload["stored_at"])
            value = payload["value"]
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

        if time.time() - stored_at > self.ttl_seconds or not isinstance(value, dict):
            return None
        return value

    def set(self, key: str, value: Mapping[str, Any]) -> None:
        """Atomically store a JSON-compatible mapping with owner-only permissions."""
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.directory, 0o700)
        path = self._path(key)
        temporary_path = path.with_suffix(".tmp")
        payload = {"stored_at": time.time(), "value": dict(value)}
        temporary_path.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        os.chmod(temporary_path, 0o600)
        temporary_path.replace(path)

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"


def inspect_cache(root: Path) -> CacheInventory:
    """Inspect cache counts and disk use without parsing or exposing content."""
    graphql_path = root / CacheTarget.GRAPHQL.value
    repositories_path = root / CacheTarget.REPOSITORIES.value
    graphql = CacheSection(
        name=CacheTarget.GRAPHQL.value,
        path=graphql_path,
        exists=graphql_path.exists(),
        entries=_graphql_entry_count(graphql_path),
        size_bytes=_path_size(graphql_path),
    )
    repositories = CacheSection(
        name=CacheTarget.REPOSITORIES.value,
        path=repositories_path,
        exists=repositories_path.exists(),
        entries=_repository_mirror_count(repositories_path),
        size_bytes=_path_size(repositories_path),
    )
    return CacheInventory(root=root, graphql=graphql, repositories=repositories)


def clear_cache(root: Path, target: CacheTarget) -> CacheClearResult:
    """Remove only explicitly named, regenerable cache sections."""
    inventory = inspect_cache(root)
    selected = (
        (inventory.graphql, inventory.repositories)
        if target is CacheTarget.ALL
        else (getattr(inventory, target.value),)
    )
    removed: list[str] = []
    reclaimed = 0
    for section in selected:
        if not section.exists:
            continue
        _remove_cache_section(section.path)
        removed.append(section.name)
        reclaimed += section.size_bytes
    return CacheClearResult(
        target=target,
        sections_removed=tuple(removed),
        bytes_reclaimed=reclaimed,
    )


def _graphql_entry_count(path: Path) -> int:
    if not path.is_dir():
        return 0
    try:
        return sum(item.is_file() and item.suffix == ".json" for item in path.iterdir())
    except OSError:
        return 0


def _repository_mirror_count(path: Path) -> int:
    if not path.is_dir():
        return 0
    try:
        return sum(
            mirror.is_dir()
            for owner in path.iterdir()
            if owner.is_dir()
            for mirror in owner.iterdir()
            if mirror.name.endswith(".git")
        )
    except OSError:
        return 0


def _path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file() or path.is_symlink():
        try:
            return path.lstat().st_size
        except OSError:
            return 0
    total = 0
    for directory, _subdirectories, filenames in os.walk(path, followlinks=False):
        for filename in filenames:
            try:
                total += (Path(directory) / filename).lstat().st_size
            except OSError:
                continue
    return total


def _remove_cache_section(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)
