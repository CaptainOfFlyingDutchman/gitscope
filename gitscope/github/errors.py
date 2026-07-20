"""Exceptions raised by GitScope's GitHub integration."""

from __future__ import annotations

from datetime import datetime


class GitHubError(RuntimeError):
    """Base class for user-facing GitHub integration failures."""


class AuthenticationError(GitHubError):
    """Raised when GitHub rejects the configured credentials."""


class GitHubAPIError(GitHubError):
    """Raised when a GitHub REST request fails."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"GitHub API returned HTTP {status_code}: {message}")


class GraphQLQueryError(GitHubError):
    """Raised when GitHub reports one or more GraphQL query errors."""


class InvalidGitHubResponseError(GitHubError):
    """Raised when GitHub returns a response that violates the expected schema."""


class OrganizationNotFoundError(GitHubError):
    """Raised when an organization is missing or invisible to the token."""


class RepositoriesNotFoundError(GitHubError):
    """Raised when allowlisted repositories are missing or inaccessible."""

    def __init__(self, repositories: list[str]) -> None:
        self.repositories = tuple(repositories)
        names = ", ".join(repositories)
        super().__init__(f"Listed repositories were not found or are inaccessible: {names}")


class RateLimitError(GitHubError):
    """Raised when GitHub refuses a request because its rate limit is exhausted."""

    def __init__(self, reset_at: datetime | None = None) -> None:
        self.reset_at = reset_at
        suffix = f" It resets at {reset_at.isoformat()}." if reset_at else ""
        super().__init__(f"GitHub API rate limit exhausted.{suffix}")


class RateLimitSafetyError(GitHubError):
    """Raised before collection consumes the configured rate-limit reserve."""

    def __init__(self, *, remaining: int, reserve: int, reset_at: datetime) -> None:
        self.remaining = remaining
        self.reserve = reserve
        self.reset_at = reset_at
        super().__init__(
            f"Collection stopped with {remaining} GraphQL points remaining to preserve the "
            f"{reserve}-point safety reserve. The limit resets at {reset_at.isoformat()}."
        )
