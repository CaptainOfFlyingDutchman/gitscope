"""Tests for GitHub collection accounting."""

from datetime import UTC, datetime

import pytest

from gitscope.github.collection import CollectionStats
from gitscope.github.errors import RateLimitSafetyError
from gitscope.github.models import RateLimit


def test_collection_stats_preserve_rate_limit_reserve() -> None:
    stats = CollectionStats(
        latest_rate_limit=RateLimit(
            cost=1,
            remaining=500,
            resetAt=datetime(2026, 7, 20, tzinfo=UTC),
        )
    )

    with pytest.raises(RateLimitSafetyError, match="500-point safety reserve"):
        stats.require_budget(500)


def test_collection_stats_distinguish_cache_hits() -> None:
    rate_limit = RateLimit(
        cost=1,
        remaining=4999,
        resetAt=datetime(2026, 7, 20, tzinfo=UTC),
    )
    stats = CollectionStats()

    stats.record(rate_limit, from_cache=False)
    stats.record(rate_limit, from_cache=True)

    assert stats.api_requests == 1
    assert stats.cache_hits == 1
    assert stats.latest_rate_limit == rate_limit
