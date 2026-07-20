"""Private on-disk JSON cache used by GitScope collectors."""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


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
