"""Private, rotating, token-sanitized diagnostic logging."""

from __future__ import annotations

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_FILE = Path(".gitscope/logs/gitscope.log")
_LOGGER_NAME = "gitscope"
_TOKEN_PATTERNS = (
    re.compile(r"\b(?:gh[pousr]|github_pat)_[A-Za-z0-9_]+\b", re.IGNORECASE),
    re.compile(r"(?i)(authorization\s*[:=]\s*(?:bearer|token)\s+)[^\s,;]+"),
    re.compile(r"(?i)(GITSCOPE_GITHUB_TOKEN\s*=\s*)[^\s,;]+"),
    re.compile(r"(https?://[^\s/:@]+:)[^\s@]+(@)", re.IGNORECASE),
)


def configure_logging(
    *,
    verbose: bool,
    log_file: Path = DEFAULT_LOG_FILE,
    secrets: tuple[str, ...] = (),
) -> logging.Logger:
    """Configure one private rotating log and an optional sanitized debug console."""
    log_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(log_file.parent, 0o700)
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()

    formatter = SanitizingFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        secrets=secrets,
    )
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    os.chmod(log_file, 0o600)
    file_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(SanitizingFormatter("DEBUG %(message)s", secrets=secrets))
        logger.addHandler(console_handler)

    logger.debug("Diagnostic logging configured; verbose=%s", verbose)
    return logger


class SanitizingFormatter(logging.Formatter):
    """Format log records while removing credentials from the final rendered text."""

    def __init__(self, format_string: str, *, secrets: tuple[str, ...] = ()) -> None:
        super().__init__(format_string)
        self.secrets = tuple(secret for secret in secrets if len(secret) >= 4)

    def format(self, record: logging.LogRecord) -> str:
        return redact_text(super().format(record), secrets=self.secrets)


def redact_text(value: str, *, secrets: tuple[str, ...] = ()) -> str:
    """Remove known and token-shaped credentials from diagnostic text."""
    redacted = value
    for secret in secrets:
        if len(secret) >= 4:
            redacted = redacted.replace(secret, "[REDACTED]")
    for pattern in _TOKEN_PATTERNS:
        if pattern.groups == 2:
            redacted = pattern.sub(r"\1[REDACTED]\2", redacted)
        elif pattern.groups == 1:
            redacted = pattern.sub(r"\1[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted
