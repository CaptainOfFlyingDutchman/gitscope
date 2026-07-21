"""Inclusive UTC date ranges shared by contribution collectors."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time


class DateRangeError(ValueError):
    """Raised when an analysis date range is malformed or inverted."""


@dataclass(frozen=True, slots=True)
class DateRange:
    """Optional inclusive calendar-date bounds interpreted in UTC."""

    since: date | None = None
    until: date | None = None

    def __post_init__(self) -> None:
        if self.since is not None and self.until is not None and self.since > self.until:
            raise DateRangeError("--since must be earlier than or equal to --until.")

    @classmethod
    def parse(cls, since: str | None, until: str | None) -> DateRange:
        """Parse exact ISO calendar dates supplied by the CLI."""
        return cls(
            since=_parse_date(since, "--since"),
            until=_parse_date(until, "--until"),
        )

    @property
    def is_lifetime(self) -> bool:
        return self.since is None and self.until is None

    def contains(self, value: datetime) -> bool:
        """Return whether an event timestamp falls within the inclusive UTC dates."""
        aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        event_date = aware.date()
        return (self.since is None or event_date >= self.since) and (
            self.until is None or event_date <= self.until
        )

    @property
    def search_qualifier(self) -> str:
        """Return GitHub's created-date search qualifier for the configured bounds."""
        if self.since is not None and self.until is not None:
            return f"created:{self.since.isoformat()}..{self.until.isoformat()}"
        if self.since is not None:
            return f"created:>={self.since.isoformat()}"
        if self.until is not None:
            return f"created:<={self.until.isoformat()}"
        return ""

    @property
    def since_timestamp(self) -> str | None:
        return _github_timestamp(self.since, time.min) if self.since is not None else None

    @property
    def until_timestamp(self) -> str | None:
        return _github_timestamp(self.until, time.max) if self.until is not None else None


LIFETIME_DATE_RANGE = DateRange()


def _parse_date(value: str | None, option: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise DateRangeError(f"{option} must use YYYY-MM-DD format.") from exc


def _github_timestamp(value: date, boundary: time) -> str:
    return datetime.combine(value, boundary, tzinfo=UTC).isoformat().replace("+00:00", "Z")
