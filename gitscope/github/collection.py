"""Shared accounting for cached, rate-aware GitHub collection."""

from __future__ import annotations

from dataclasses import dataclass, field

from gitscope.github.errors import RateLimitSafetyError
from gitscope.github.models import RateLimit


@dataclass(slots=True)
class CollectionStats:
    """Mutable accounting accumulated during a collection workflow."""

    api_requests: int = 0
    cache_hits: int = 0
    latest_rate_limit: RateLimit | None = None
    warnings: list[str] = field(default_factory=list)

    def record(self, rate_limit: RateLimit, *, from_cache: bool) -> None:
        """Record one cached response or live GraphQL request."""
        if from_cache:
            self.cache_hits += 1
        else:
            self.api_requests += 1
            self.latest_rate_limit = rate_limit

    def require_budget(self, reserve: int) -> None:
        """Stop pagination before consuming the configured safety reserve."""
        if self.latest_rate_limit and self.latest_rate_limit.remaining <= reserve:
            raise RateLimitSafetyError(
                remaining=self.latest_rate_limit.remaining,
                reserve=reserve,
                reset_at=self.latest_rate_limit.reset_at,
            )

    def merge(self, other: CollectionStats) -> None:
        """Merge another collector's accounting into this instance."""
        self.api_requests += other.api_requests
        self.cache_hits += other.cache_hits
        self.warnings.extend(other.warnings)
        if other.latest_rate_limit is not None:
            self.latest_rate_limit = other.latest_rate_limit
