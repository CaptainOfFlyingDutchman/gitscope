"""Explicit and GitHub-derived author identity matching."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_IDENTITIES_FILE = Path(".gitscope-identities")


class IdentityFileError(ValueError):
    """Raised when an author identity file is malformed."""


@dataclass(frozen=True, slots=True)
class AuthorIdentities:
    """Case-insensitive exact names and emails identifying one author."""

    names: frozenset[str]
    emails: frozenset[str]

    @classmethod
    def build(
        cls,
        *,
        username: str,
        database_id: int,
        github_name: str | None = None,
        source: Path = DEFAULT_IDENTITIES_FILE,
    ) -> AuthorIdentities:
        names = {username.casefold()}
        emails = {
            f"{username}@users.noreply.github.com".casefold(),
            f"{database_id}+{username}@users.noreply.github.com".casefold(),
        }
        if github_name and github_name.strip():
            names.add(github_name.strip().casefold())
        if source.exists():
            _load_identity_file(source, names, emails)
        return cls(names=frozenset(names), emails=frozenset(emails))

    def matches(self, name: str, email: str) -> bool:
        """Match an author by exact normalized email or name."""
        return email.strip().casefold() in self.emails or name.strip().casefold() in self.names


def _load_identity_file(source: Path, names: set[str], emails: set[str]) -> None:
    for line_number, raw_line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        kind, separator, value = line.partition(":")
        normalized_value = value.strip().casefold()
        if (
            not separator
            or kind.strip().casefold() not in {"name", "email"}
            or not normalized_value
        ):
            raise IdentityFileError(
                f"{source}:{line_number}: expected 'name: value' or 'email: value'"
            )
        if kind.strip().casefold() == "name":
            names.add(normalized_value)
        else:
            emails.add(normalized_value)
