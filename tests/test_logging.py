"""Tests for private sanitized diagnostic logging."""

import logging
import stat
from pathlib import Path

from gitscope.logging import configure_logging, redact_text


def test_redact_text_removes_known_and_token_shaped_credentials() -> None:
    secret = "arbitrary-secret-value"
    value = (
        "token arbitrary-secret-value ghp_abcdefghijklmnopqrstuvwxyz "
        "Authorization: Bearer sensitive-value "
        "https://x-access-token:password@example.com/repo.git"
    )

    redacted = redact_text(value, secrets=(secret,))

    assert secret not in redacted
    assert "ghp_" not in redacted
    assert "sensitive-value" not in redacted
    assert "password" not in redacted
    assert redacted.count("[REDACTED]") == 4


def test_configure_logging_writes_private_rotating_sanitized_log(tmp_path: Path) -> None:
    log_file = tmp_path / "logs" / "gitscope.log"
    secret = "classic-token-secret"
    logger = configure_logging(verbose=False, log_file=log_file, secrets=(secret,))

    logging.getLogger("gitscope.test").warning("request failed with %s", secret)
    for handler in logger.handlers:
        handler.flush()

    content = log_file.read_text(encoding="utf-8")
    assert secret not in content
    assert "[REDACTED]" in content
    assert stat.S_IMODE(log_file.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(log_file.stat().st_mode) == 0o600
