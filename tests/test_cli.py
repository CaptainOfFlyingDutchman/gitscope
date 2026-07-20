"""Tests for the GitScope CLI."""

from typer.testing import CliRunner

from gitscope import __version__
from gitscope.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"GitScope {__version__}" in result.stdout


def test_analyze_requires_token() -> None:
    result = runner.invoke(
        app,
        ["analyze", "--org", "josys-src", "--user", "CaptainOfFlyingDutchman"],
        env={"GITHUB_TOKEN": ""},
    )

    assert result.exit_code == 2
    assert "GITHUB_TOKEN is not configured" in result.stderr


def test_analyze_accepts_valid_configuration() -> None:
    result = runner.invoke(
        app,
        ["analyze", "--org", "josys-src", "--user", "CaptainOfFlyingDutchman"],
        env={"GITHUB_TOKEN": "secret-token"},
    )

    assert result.exit_code == 0
    assert "Ready to analyze CaptainOfFlyingDutchman in josys-src" in result.stdout
