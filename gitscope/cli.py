"""Command-line interface for GitScope."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from gitscope import __version__
from gitscope.cache import CacheTarget, clear_cache, inspect_cache
from gitscope.config import ConfigurationError, Settings
from gitscope.date_range import DateRange, DateRangeError
from gitscope.diagnostics import DiagnosticStatus, run_diagnostics
from gitscope.git.identities import DEFAULT_IDENTITIES_FILE, IdentityFileError
from gitscope.github.discovery import DiscoveryContext
from gitscope.github.errors import GitHubError
from gitscope.logging import DEFAULT_LOG_FILE, configure_logging
from gitscope.models.report import CareerReport
from gitscope.report.export import ExportFormat, ReportExportError, export_existing_report
from gitscope.report.generate import generate_career_report
from gitscope.report.resume import ResumeError, generate_resume_portfolio
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
export_app = typer.Typer(
    help="Regenerate report outputs locally from an existing report.json.",
    no_args_is_help=True,
)
app.add_typer(export_app, name="export")
cache_app = typer.Typer(
    help="Inspect and manage regenerable local cache content.",
    no_args_is_help=True,
)
app.add_typer(cache_app, name="cache")
console = Console()
error_console = Console(stderr=True)
logger = logging.getLogger("gitscope.cli")


def version_callback(value: bool) -> None:
    """Print the installed version and exit."""
    if value:
        console.print(f"GitScope {__version__}")
        raise typer.Exit


@app.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show sanitized diagnostic logging."),
    ] = False,
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version."),
    ] = None,
) -> None:
    """Generate an engineering career report from a GitHub organization."""
    load_dotenv()
    configure_logging(
        verbose=verbose,
        secrets=(os.environ.get("GITHUB_TOKEN", ""),),
    )


@app.command()
def analyze(
    organization: Annotated[str, typer.Option("--org", help="GitHub organization login.")],
    username: Annotated[str, typer.Option("--user", help="GitHub user login.")],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Directory for generated report files."),
    ] = Path("career-report"),
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            help="Include contributions on or after this UTC date (YYYY-MM-DD).",
        ),
    ] = None,
    until: Annotated[
        str | None,
        typer.Option(
            "--until",
            help="Include contributions on or before this UTC date (YYYY-MM-DD).",
        ),
    ] = None,
    refresh: Annotated[
        bool,
        typer.Option("--refresh", help="Ignore cached GitHub responses."),
    ] = False,
    repositories_file: Annotated[
        Path | None,
        typer.Option(
            "--repos-file",
            help=(
                "Private allowlist containing one owner/name repository per line. "
                "Defaults to .gitscope-repositories."
            ),
        ),
    ] = None,
    all_repositories: Annotated[
        bool,
        typer.Option(
            "--all-repositories",
            help="Analyze every organization repository visible to the GitHub token.",
        ),
    ] = False,
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
    logger.info("Analysis started")
    if all_repositories and repositories_file is not None:
        error_console.print(
            "[bold red]Repository selection error:[/bold red] "
            "--all-repositories cannot be combined with --repos-file."
        )
        raise typer.Exit(code=2)

    try:
        date_range = DateRange.parse(since, until)
    except DateRangeError as exc:
        error_console.print(f"[bold red]Date range error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    try:
        settings = Settings.from_environment(
            organization=organization,
            username=username,
            output_directory=output,
        )
    except ConfigurationError as exc:
        logger.warning("Analysis configuration failed: %s", type(exc).__name__)
        error_console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    if all_repositories:
        repository_scope = RepositoryScope.all_visible(organization=settings.organization)
        console.print(
            "[bold yellow]All-repositories mode:[/bold yellow] every repository in "
            f"[bold]{settings.organization}[/bold] visible to this token will be inspected; "
            "only contribution candidates will be cloned."
        )
    else:
        try:
            repository_scope = RepositoryScope.from_file(
                repositories_file or DEFAULT_REPOSITORIES_FILE,
                organization=settings.organization,
            )
        except RepositoryScopeError as exc:
            logger.warning("Repository scope validation failed: %s", type(exc).__name__)
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
                    date_range=date_range,
                    scope_observer=(_print_all_repositories_scope if all_repositories else None),
                    git_scope_observer=(_print_selected_git_scope if all_repositories else None),
                )
            )
    except (GitHubError, IdentityFileError) as exc:
        logger.exception("Analysis collection failed: %s", type(exc).__name__)
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
    repository_label = "visible" if repository_scope.all_repositories else "allowlisted"
    console.print(
        f"Validated [bold]{repository_count}[/bold] {repository_label} repositories in "
        f"[bold]{settings.organization}[/bold] "
        f"([bold]{private_count}[/bold] private)."
    )
    console.print(f"Source: {context.discovery.source.replace('-', ' ')}.")
    if not date_range.is_lifetime:
        start = date_range.since.isoformat() if date_range.since else "the beginning"
        end = date_range.until.isoformat() if date_range.until else "present"
        console.print(f"Analysis window (UTC): [bold]{start}[/bold] through [bold]{end}[/bold].")
    _print_contribution_summary(report)
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
    console.print(
        f"[green]Wrote[/green] [bold]{len(generated.chart_paths)}[/bold] interactive charts."
    )
    if generated.html_path is not None:
        console.print(f"[green]Wrote[/green] dashboard [bold]{generated.html_path}[/bold].")
    if generated.markdown_path is not None:
        console.print(
            f"[green]Wrote[/green] Markdown report [bold]{generated.markdown_path}[/bold]."
        )
    if generated.csv_path is not None:
        console.print(f"[green]Wrote[/green] CSV export [bold]{generated.csv_path}[/bold].")
    console.print(f"[green]Wrote[/green] [bold]{generated.path}[/bold].")
    logger.info(
        "Analysis completed: repositories=%d commits=%d pull_requests=%d issues=%d reviews=%d",
        repository_count,
        report.commit_summary.total,
        report.pull_request_summary.total,
        report.issue_summary.total,
        report.review_summary.total,
    )


def _print_all_repositories_scope(context: DiscoveryContext) -> None:
    """Confirm the resolved all-repositories scope before deeper collection begins."""
    repositories = context.discovery.repositories
    private_count = sum(repository.is_private for repository in repositories)
    console.print(
        f"[bold yellow]Resolved all-repositories scope:[/bold yellow] "
        f"[bold]{len(repositories)}[/bold] visible repositories "
        f"([bold]{private_count}[/bold] private). "
        "Inspecting contribution metadata before Git cloning."
    )


def _print_selected_git_scope(inspected: int, selected: int) -> None:
    """Report how many visible repositories need full-history Git analysis."""
    console.print(
        f"[bold yellow]Contribution prefilter:[/bold yellow] selected "
        f"[bold]{selected}[/bold] of [bold]{inspected}[/bold] visible repositories "
        "for full-history Git analysis."
    )


@cache_app.command("status")
def cache_status(
    cache_directory: Annotated[
        Path,
        typer.Option("--cache-dir", help="GitScope cache directory."),
    ] = Path(".gitscope/cache"),
) -> None:
    """Show content-free cache counts and disk usage."""
    with console.status("Inspecting local cache metadata..."):
        inventory = inspect_cache(cache_directory)
    table = Table(title="GitScope cache", show_edge=False, pad_edge=False)
    table.add_column("Section", style="cyan")
    table.add_column("Entries", justify="right")
    table.add_column("Disk use", justify="right")
    table.add_column("State")
    for section in (inventory.graphql, inventory.repositories):
        table.add_row(
            section.name,
            f"{section.entries:,}",
            _format_bytes(section.size_bytes),
            "present" if section.exists else "not created",
        )
    table.add_row("Total", "", _format_bytes(inventory.size_bytes), "")
    console.print(table)
    console.print(f"Cache root: [bold]{cache_directory.resolve()}[/bold]")
    console.print("[dim]Cached payload contents and repository names are not displayed.[/dim]")
    logger.info(
        "Cache inspected: graphql_entries=%d repository_mirrors=%d bytes=%d",
        inventory.graphql.entries,
        inventory.repositories.entries,
        inventory.size_bytes,
    )


@cache_app.command("path")
def cache_path(
    cache_directory: Annotated[
        Path,
        typer.Option("--cache-dir", help="GitScope cache directory."),
    ] = Path(".gitscope/cache"),
) -> None:
    """Print the configured cache location without inspecting content."""
    console.print(cache_directory.resolve())
    logger.info("Cache path displayed")


@cache_app.command("clear")
def cache_clear(
    target: Annotated[
        CacheTarget,
        typer.Argument(help="Cache section to clear: graphql, repositories, or all."),
    ],
    cache_directory: Annotated[
        Path,
        typer.Option("--cache-dir", help="GitScope cache directory."),
    ] = Path(".gitscope/cache"),
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip the confirmation prompt."),
    ] = False,
) -> None:
    """Clear an explicit regenerable cache section after confirmation."""
    if not yes:
        confirmed = typer.confirm(
            f"Clear the '{target.value}' GitScope cache under {cache_directory}?"
        )
        if not confirmed:
            console.print("Cache clear cancelled; nothing was removed.")
            raise typer.Exit
    with console.status("Clearing selected cache content..."):
        result = clear_cache(cache_directory, target)
    if result.sections_removed:
        sections = ", ".join(result.sections_removed)
        console.print(
            f"[green]Cleared[/green] [bold]{sections}[/bold]; reclaimed approximately "
            f"[bold]{_format_bytes(result.bytes_reclaimed)}[/bold]."
        )
    else:
        console.print("Selected cache content was already absent; nothing was removed.")
    console.print("[dim]Reports, logs, configuration, and allowlist files were preserved.[/dim]")
    logger.info(
        "Cache cleared: target=%s sections=%d bytes=%d",
        target.value,
        len(result.sections_removed),
        result.bytes_reclaimed,
    )


@app.command()
def doctor(
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Existing report.json to validate."),
    ] = Path("career-report/report.json"),
    repositories_file: Annotated[
        Path,
        typer.Option("--repos-file", help="Repository allowlist to inspect safely."),
    ] = DEFAULT_REPOSITORIES_FILE,
    cache_directory: Annotated[
        Path,
        typer.Option("--cache-dir", help="GitScope cache directory."),
    ] = Path(".gitscope/cache"),
) -> None:
    """Run local environment diagnostics without contacting GitHub."""
    with console.status("Running local diagnostics..."):
        diagnostic_report = run_diagnostics(
            cache_directory=cache_directory,
            report_path=report_path,
            repositories_file=repositories_file,
            log_file=DEFAULT_LOG_FILE,
            token_present=bool(os.environ.get("GITHUB_TOKEN", "").strip()),
        )
    table = Table(title="GitScope doctor", show_edge=False, pad_edge=False)
    table.add_column("Status")
    table.add_column("Check", style="cyan")
    table.add_column("Detail")
    status_styles = {
        DiagnosticStatus.PASS: "green",
        DiagnosticStatus.WARN: "yellow",
        DiagnosticStatus.FAIL: "bold red",
    }
    for check in diagnostic_report.checks:
        table.add_row(
            f"[{status_styles[check.status]}]{check.status.value}[/{status_styles[check.status]}]",
            check.name,
            check.detail,
        )
    console.print(table)
    console.print(
        "[dim]Diagnostics are local-only; token values and cache payloads are hidden.[/dim]"
    )
    logger.info(
        "Diagnostics completed: checks=%d failures=%d",
        len(diagnostic_report.checks),
        sum(check.status is DiagnosticStatus.FAIL for check in diagnostic_report.checks),
    )
    if diagnostic_report.has_failures:
        raise typer.Exit(code=1)


@export_app.command("html")
def export_html(
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Existing GitScope report.json."),
    ] = Path("career-report/report.json"),
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Directory for regenerated output files."),
    ] = None,
) -> None:
    """Regenerate the offline HTML dashboard and its local runtime."""
    _run_offline_export(report_path, output, ("html",))


@export_app.command("markdown")
def export_markdown(
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Existing GitScope report.json."),
    ] = Path("career-report/report.json"),
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Directory for regenerated output files."),
    ] = None,
) -> None:
    """Regenerate the portable Markdown report."""
    _run_offline_export(report_path, output, ("markdown",))


@export_app.command("csv")
def export_csv(
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Existing GitScope report.json."),
    ] = Path("career-report/report.json"),
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Directory for regenerated output files."),
    ] = None,
) -> None:
    """Regenerate the spreadsheet-friendly CSV ledger."""
    _run_offline_export(report_path, output, ("csv",))


@export_app.command("charts")
def export_charts(
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Existing GitScope report.json."),
    ] = Path("career-report/report.json"),
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Directory for regenerated output files."),
    ] = None,
) -> None:
    """Regenerate every standalone interactive chart."""
    _run_offline_export(report_path, output, ("charts",))


@export_app.command("all")
def export_all(
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Existing GitScope report.json."),
    ] = Path("career-report/report.json"),
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Directory for regenerated output files."),
    ] = None,
) -> None:
    """Regenerate HTML, Markdown, CSV, and all chart pages."""
    _run_offline_export(report_path, output, ("charts", "html", "markdown", "csv"))


def _run_offline_export(
    report_path: Path,
    output: Path | None,
    formats: tuple[ExportFormat, ...],
) -> None:
    try:
        with console.status("Regenerating report outputs locally..."):
            exported = export_existing_report(
                report_path,
                output,
                formats=formats,
            )
    except ReportExportError as exc:
        logger.warning("Offline export failed: %s", type(exc).__name__)
        error_console.print(f"[bold red]Export error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    report = exported.report
    console.print(
        f"Loaded GitScope schema [bold]{report.schema_version}[/bold] for "
        f"[bold]{report.identity.username}[/bold] in [bold]{report.organization}[/bold]."
    )
    _print_contribution_summary(report)
    chart_paths = tuple(path for path in exported.paths if path.parent.name == "charts")
    if chart_paths:
        console.print(
            f"[green]Wrote[/green] [bold]{len(chart_paths)}[/bold] interactive charts to "
            f"[bold]{chart_paths[0].parent}[/bold]."
        )
    for path in exported.paths:
        if path in chart_paths:
            continue
        label = {
            ".html": "dashboard",
            ".md": "Markdown report",
            ".csv": "CSV export",
        }.get(path.suffix, "report output")
        console.print(f"[green]Wrote[/green] {label} [bold]{path}[/bold].")
    console.print(
        "[dim]Offline export complete; no GitHub API or Git repository access used.[/dim]"
    )
    logger.info(
        "Offline export completed: formats=%s outputs=%d",
        ",".join(exported.formats),
        len(exported.paths),
    )


def _print_contribution_summary(report: CareerReport) -> None:
    table = Table(title="Contribution summary", show_edge=False, pad_edge=False)
    table.add_column("Activity", style="cyan")
    table.add_column("Count", justify="right", style="bold")
    table.add_row("Authored commits", f"{report.commit_summary.total:,}")
    table.add_row("Authored pull requests", f"{report.pull_request_summary.total:,}")
    table.add_row("Authored issues", f"{report.issue_summary.total:,}")
    table.add_row("Submitted reviews", f"{report.review_summary.total:,}")
    table.add_row("Repositories in scope", f"{report.collection.repository_count:,}")
    table.add_row("Active days", f"{report.timeline.active_days:,}")
    console.print(table)


def _format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


@app.command()
def resume(
    report_path: Annotated[
        Path,
        typer.Option(
            "--report",
            help="Existing GitScope report.json; no GitHub API calls are made.",
        ),
    ] = Path("career-report/report.json"),
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Directory for resume.md and resume.html."),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", help="Professional display name; defaults to GitHub username."),
    ] = None,
    title: Annotated[
        str,
        typer.Option("--title", help="Current professional title."),
    ] = "Software Engineer",
    company: Annotated[
        str | None,
        typer.Option("--company", help="Current company; defaults to report organization."),
    ] = None,
    website: Annotated[
        str | None,
        typer.Option("--site", help="Optional HTTP(S) professional website."),
    ] = None,
) -> None:
    """Generate an offline contribution résumé from an existing JSON report."""
    try:
        generated = generate_resume_portfolio(
            report_path,
            output or report_path.parent,
            name=name,
            title=title,
            company=company,
            website=website,
        )
    except (ResumeError, ValidationError) as exc:
        logger.warning("Resume generation failed: %s", type(exc).__name__)
        error_console.print(f"[bold red]Resume error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    profile = generated.document.profile
    console.print(
        f"[bold]{profile.name}[/bold] · [bold]{profile.title}[/bold] at "
        f"[bold]{profile.company}[/bold]"
    )
    console.print(generated.document.summary)
    console.print(f"[green]Wrote[/green] Markdown résumé [bold]{generated.markdown_path}[/bold].")
    console.print(f"[green]Wrote[/green] HTML résumé [bold]{generated.html_path}[/bold].")
    logger.info("Resume generation completed: outputs=2")
