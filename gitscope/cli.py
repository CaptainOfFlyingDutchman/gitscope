"""Command-line interface for GitScope."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console

from gitscope import __version__
from gitscope.config import ConfigurationError, Settings
from gitscope.github.discovery import discover_repositories
from gitscope.github.errors import GitHubError

app = typer.Typer(
    name="gitscope",
    help="Generate an engineering career report from a GitHub organization.",
    no_args_is_help=True,
)
console = Console()
error_console = Console(stderr=True)


def version_callback(value: bool) -> None:
    """Print the installed version and exit."""
    if value:
        console.print(f"GitScope {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version."),
    ] = None,
) -> None:
    """Generate an engineering career report from a GitHub organization."""


@app.command()
def analyze(
    organization: Annotated[str, typer.Option("--org", help="GitHub organization login.")],
    username: Annotated[str, typer.Option("--user", help="GitHub user login.")],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Directory for generated report files."),
    ] = Path("career-report"),
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignore cached GitHub responses."),
    ] = False,
) -> None:
    """Validate access and discover repositories for an organization analysis."""
    load_dotenv()
    try:
        settings = Settings.from_environment(
            organization=organization,
            username=username,
            output_directory=output,
        )
    except ConfigurationError as exc:
        error_console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    try:
        with console.status("Connecting to GitHub..."):
            context = asyncio.run(discover_repositories(settings, refresh=refresh))
    except GitHubError as exc:
        error_console.print(f"[bold red]GitHub error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    repository_count = len(context.discovery.repositories)
    private_count = sum(repository.is_private for repository in context.discovery.repositories)
    console.print(
        f"[green]Authenticated as[/green] [bold]{context.authenticated_user.login}[/bold]."
    )
    console.print(
        f"Found [bold]{repository_count}[/bold] visible repositories in "
        f"[bold]{settings.organization}[/bold] "
        f"([bold]{private_count}[/bold] private) via {context.discovery.source}."
    )
    if context.discovery.rate_limit:
        console.print(
            f"GraphQL rate limit remaining: "
            f"[bold]{context.discovery.rate_limit.remaining:,}[/bold]."
        )
