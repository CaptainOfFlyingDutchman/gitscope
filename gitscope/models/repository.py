"""Repository domain values shared across collectors and reports."""

from enum import StrEnum


class RepositoryVisibility(StrEnum):
    """Visibility of a source-code repository."""

    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    INTERNAL = "INTERNAL"
