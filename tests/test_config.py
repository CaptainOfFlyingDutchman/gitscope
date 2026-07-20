"""Tests for GitScope configuration."""

from pathlib import Path

import pytest

from gitscope.config import ConfigurationError, Settings


def test_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", " secret-token ")

    settings = Settings.from_environment(
        organization=" josys-src ",
        username=" CaptainOfFlyingDutchman ",
        output_directory=Path("output"),
    )

    assert settings.organization == "josys-src"
    assert settings.username == "CaptainOfFlyingDutchman"
    assert settings.github_token == "secret-token"
    assert settings.output_directory == Path("output")


def test_settings_require_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(ConfigurationError, match="GITHUB_TOKEN"):
        Settings.from_environment(organization="josys-src", username="octocat")


@pytest.mark.parametrize(("organization", "username"), [("", "octocat"), ("github", "")])
def test_settings_require_non_empty_logins(
    monkeypatch: pytest.MonkeyPatch,
    organization: str,
    username: str,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")

    with pytest.raises(ConfigurationError):
        Settings.from_environment(organization=organization, username=username)
