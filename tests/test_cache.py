"""Tests for the private JSON cache."""

import json
import stat
from pathlib import Path

import pytest

from gitscope.cache import CacheTarget, JsonCache, clear_cache, inspect_cache


def test_cache_round_trip_uses_private_permissions(tmp_path: Path) -> None:
    cache = JsonCache(tmp_path / "private-cache")
    key = cache.key_for("graphql", {"login": "josys-src"})

    cache.set(key, {"repositories": ["example"]})

    assert cache.get(key) == {"repositories": ["example"]}
    directory_mode = stat.S_IMODE(cache.directory.stat().st_mode)
    file_mode = stat.S_IMODE(next(cache.directory.iterdir()).stat().st_mode)
    assert directory_mode == 0o700
    assert file_mode == 0o600


def test_cache_ignores_expired_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = JsonCache(tmp_path, ttl_seconds=10)
    monkeypatch.setattr("gitscope.cache.time.time", lambda: 100.0)
    cache.set("key", {"value": 1})
    monkeypatch.setattr("gitscope.cache.time.time", lambda: 111.0)

    assert cache.get("key") is None


def test_cache_ignores_malformed_entries(tmp_path: Path) -> None:
    cache = JsonCache(tmp_path)
    (tmp_path / "bad.json").write_text(json.dumps({"not": "an entry"}), encoding="utf-8")

    assert cache.get("bad") is None


def test_cache_inventory_reports_metadata_without_reading_payloads(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    graphql = root / "graphql"
    graphql.mkdir(parents=True)
    (graphql / "one.json").write_text("private payload", encoding="utf-8")
    (graphql / "temporary.tmp").write_text("ignored", encoding="utf-8")
    mirror = root / "repositories" / "org" / "repo.git"
    mirror.mkdir(parents=True)
    (mirror / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")

    inventory = inspect_cache(root)

    assert inventory.graphql.entries == 1
    assert inventory.repositories.entries == 1
    assert inventory.size_bytes > 0


def test_cache_clear_removes_only_selected_regenerable_section(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    graphql = root / "graphql"
    repository = root / "repositories" / "org" / "repo.git"
    graphql.mkdir(parents=True)
    repository.mkdir(parents=True)
    (graphql / "one.json").write_text("payload", encoding="utf-8")
    (repository / "HEAD").write_text("ref", encoding="utf-8")
    preserved = root.parent / "logs" / "gitscope.log"
    preserved.parent.mkdir()
    preserved.write_text("log", encoding="utf-8")

    result = clear_cache(root, CacheTarget.GRAPHQL)

    assert result.sections_removed == ("graphql",)
    assert result.bytes_reclaimed > 0
    assert not graphql.exists()
    assert repository.exists()
    assert preserved.exists()

    all_result = clear_cache(root, CacheTarget.ALL)

    assert all_result.sections_removed == ("repositories",)
    assert not repository.exists()
    assert root.exists()
