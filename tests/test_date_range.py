"""Tests for inclusive UTC analysis windows."""

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from gitscope.date_range import DateRange, DateRangeError


def test_date_range_parses_inclusive_bounds_and_qualifiers() -> None:
    window = DateRange.parse("2025-01-01", "2025-12-31")

    assert window.since == date(2025, 1, 1)
    assert window.until == date(2025, 12, 31)
    assert window.search_qualifier == "created:2025-01-01..2025-12-31"
    assert window.contains(datetime(2025, 1, 1, tzinfo=UTC))
    assert window.contains(datetime(2026, 1, 1, 4, tzinfo=timezone(timedelta(hours=5))))
    assert not window.contains(datetime(2026, 1, 1, 6, tzinfo=timezone(timedelta(hours=5))))

    assert DateRange.parse("2025-01-01", None).search_qualifier == "created:>=2025-01-01"
    assert DateRange.parse(None, "2025-12-31").search_qualifier == "created:<=2025-12-31"


@pytest.mark.parametrize(
    ("since", "until", "message"),
    [
        ("not-a-date", None, "--since must use YYYY-MM-DD format"),
        ("2026-02-01", "2026-01-01", "--since must be earlier"),
    ],
)
def test_date_range_rejects_invalid_input(
    since: str | None,
    until: str | None,
    message: str,
) -> None:
    with pytest.raises(DateRangeError, match=message):
        DateRange.parse(since, until)
