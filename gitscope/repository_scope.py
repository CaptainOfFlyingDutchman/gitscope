"""Parsing and validation for the private repository allowlist."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REPOSITORIES_FILE = Path(".gitscope-repositories")
REPOSITORY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


class RepositoryScopeError(ValueError):
    """Raised when a repository allowlist cannot be used safely."""


@dataclass(frozen=True, slots=True)
class RepositoryScope:
    """Ordered, deduplicated repository names within one organization."""

    organization: str
    names: tuple[str, ...]
    source: Path | None
    all_repositories: bool = False

    @classmethod
    def all_visible(cls, *, organization: str) -> RepositoryScope:
        """Select every organization repository visible to the configured token."""
        return cls(
            organization=organization,
            names=(),
            source=None,
            all_repositories=True,
        )

    @property
    def source_label(self) -> str:
        """Return a stable report label for the selected repository source."""
        return "--all-repositories" if self.all_repositories else str(self.source)

    @classmethod
    def from_file(cls, path: Path, *, organization: str) -> RepositoryScope:
        """Load an allowlist and reject malformed or cross-organization entries."""
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError as exc:
            raise RepositoryScopeError(
                f"Repository list '{path}' does not exist. Create it with one owner/name per line."
            ) from exc
        except OSError as exc:
            raise RepositoryScopeError(f"Repository list '{path}' could not be read.") from exc

        names: list[str] = []
        seen: set[str] = set()
        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            owner, separator, name = line.partition("/")
            if not separator or "/" in name or not owner or not name:
                raise RepositoryScopeError(
                    f"Invalid repository on line {line_number}: expected owner/name."
                )
            if owner.casefold() != organization.casefold():
                raise RepositoryScopeError(
                    f"Repository on line {line_number} belongs to '{owner}', not '{organization}'."
                )
            if not REPOSITORY_NAME_PATTERN.fullmatch(name):
                raise RepositoryScopeError(
                    f"Invalid repository name on line {line_number}: '{name}'."
                )
            normalized_name = name.casefold()
            if normalized_name not in seen:
                seen.add(normalized_name)
                names.append(name)

        if not names:
            raise RepositoryScopeError(f"Repository list '{path}' contains no repositories.")
        return cls(
            organization=organization,
            names=tuple(names),
            source=path,
            all_repositories=False,
        )
