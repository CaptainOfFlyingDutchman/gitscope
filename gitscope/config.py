"""Runtime configuration and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(ValueError):
    """Raised when required GitScope configuration is invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuration required for an organization analysis."""

    organization: str
    username: str
    github_token: str
    output_directory: Path = Path("career-report")
    cache_directory: Path = Path(".gitscope/cache")

    @classmethod
    def from_environment(
        cls,
        *,
        organization: str,
        username: str,
        output_directory: Path = Path("career-report"),
    ) -> Settings:
        """Create settings using a token supplied through the process environment."""
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if not token:
            raise ConfigurationError(
                "GITHUB_TOKEN is not configured. "
                "Set it in your environment before running GitScope."
            )

        normalized_organization = organization.strip()
        normalized_username = username.strip()
        if not normalized_organization:
            raise ConfigurationError("Organization must not be empty.")
        if not normalized_username:
            raise ConfigurationError("Username must not be empty.")

        return cls(
            organization=normalized_organization,
            username=normalized_username,
            github_token=token,
            output_directory=output_directory,
        )
