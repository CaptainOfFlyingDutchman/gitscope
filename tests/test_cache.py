"""Tests for the private JSON cache."""

import json
import stat
from pathlib import Path

import pytest

from gitscope.cache import JsonCache


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
