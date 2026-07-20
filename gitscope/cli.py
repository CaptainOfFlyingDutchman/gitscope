"""Command-line interface for GitScope."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console

from gitscope import __version__
from gitscope.config import ConfigurationError, Settings

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
) -> None:
    """Analyze a user's contributions within one GitHub organization."""
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

    console.print(
        "[green]Configuration valid.[/green] "
        f"Ready to analyze [bold]{settings.username}[/bold] in "
        f"[bold]{settings.organization}[/bold]."
    )
