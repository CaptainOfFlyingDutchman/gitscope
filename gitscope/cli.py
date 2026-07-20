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
from gitscope.git.identities import DEFAULT_IDENTITIES_FILE, IdentityFileError
from gitscope.github.errors import GitHubError
from gitscope.report.generate import generate_career_report
from gitscope.repository_scope import (
    DEFAULT_REPOSITORIES_FILE,
    RepositoryScope,
    RepositoryScopeError,
)

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
    repositories_file: Annotated[
        Path,
        typer.Option(
            "--repos-file",
            help="Private allowlist containing one owner/name repository per line.",
        ),
    ] = DEFAULT_REPOSITORIES_FILE,
    identities_file: Annotated[
        Path,
        typer.Option(
            "--identities-file",
            help="Optional private file containing historical Git author names and emails.",
        ),
    ] = DEFAULT_IDENTITIES_FILE,
    git_concurrency: Annotated[
        int,
        typer.Option(
            "--git-concurrency",
            min=1,
            max=16,
            help="Number of repositories to clone and inspect concurrently.",
        ),
    ] = 4,
) -> None:
    """Collect scoped contributions and write a versioned JSON career report."""
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
        repository_scope = RepositoryScope.from_file(
            repositories_file,
            organization=settings.organization,
        )
    except RepositoryScopeError as exc:
        error_console.print(f"[bold red]Repository list error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    try:
        with console.status("Collecting GitHub contributions..."):
            generated = asyncio.run(
                generate_career_report(
                    settings,
                    repository_scope,
                    refresh=refresh,
                    identities_file=identities_file,
                    git_concurrency=git_concurrency,
                )
            )
    except (GitHubError, IdentityFileError) as exc:
        label = "GitHub error" if isinstance(exc, GitHubError) else "Identity file error"
        error_console.print(f"[bold red]{label}:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    report = generated.report
    context = generated.discovery_context
    repository_count = len(report.repositories)
    private_count = sum(repository.visibility == "PRIVATE" for repository in report.repositories)
    console.print(
        f"[green]Authenticated as[/green] [bold]{context.authenticated_user.login}[/bold]."
    )
    console.print(
        f"Validated [bold]{repository_count}[/bold] allowlisted repositories in "
        f"[bold]{settings.organization}[/bold] "
        f"([bold]{private_count}[/bold] private)."
    )
    console.print(f"Source: {context.discovery.source.replace('-', ' ')}.")
    console.print(
        f"Collected [bold]{report.commit_summary.total}[/bold] authored commits, "
        f"[bold]{report.pull_request_summary.total}[/bold] authored pull requests, and "
        f"[bold]{report.review_summary.total}[/bold] submitted reviews."
    )
    console.print(
        f"Classified contributed changes across "
        f"[bold]{len(report.language_summary.contributed_languages)}[/bold] inferred languages "
        f"and [bold]{len(report.language_summary.file_extensions)}[/bold] file extensions."
    )
    console.print(
        f"Built a contribution timeline spanning "
        f"[bold]{report.timeline.career_span_days:,}[/bold] days with "
        f"[bold]{len(report.timeline.milestones)}[/bold] career milestones."
    )
    if report.collection.graphql_rate_limit_remaining is not None:
        console.print(
            f"GraphQL rate limit remaining: "
            f"[bold]{report.collection.graphql_rate_limit_remaining:,}[/bold]."
        )
    else:
        console.print("GitHub contribution metadata loaded from cache.")
    if report.collection.warnings:
        console.print(f"[yellow]Warnings:[/yellow] {len(report.collection.warnings)}")
    console.print(f"[green]Wrote[/green] [bold]{generated.path}[/bold].")
