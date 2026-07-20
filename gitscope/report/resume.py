"""Deterministic résumé portfolio derivation and rendering."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from gitscope.models.report import CareerMilestone, CareerReport
from gitscope.models.resume import ResumeDocument, ResumeMetric, ResumeMilestone, ResumeProfile

_TEMPLATE_DIRECTORY = Path(__file__).parent.parent / "templates"
_MILESTONE_PRIORITY = {
    "first_contribution",
    "commit_100",
    "commit_500",
    "commit_1000",
    "first_merged_pull_request",
    "pull_request_100",
    "review_1000",
    "review_2500",
    "last_contribution",
}
_RESUME_TECHNOLOGY_EXCLUSIONS = {
    "dependency lockfile",
    "json",
    "markdown",
    "mdx",
    "other",
    "svg",
    "test snapshot",
    "text",
    "unknown",
    "xml",
    "yaml",
}
_RESUME_TECHNOLOGY_LABELS = {"Dockerfile": "Docker"}


class ResumeError(RuntimeError):
    """Raised when a résumé portfolio cannot be generated safely."""


@dataclass(frozen=True, slots=True)
class GeneratedResumePortfolio:
    """Structured résumé and synchronized generated paths."""

    document: ResumeDocument
    markdown_path: Path
    html_path: Path


def generate_resume_portfolio(
    report_path: Path,
    output_directory: Path,
    profile: ResumeProfile | None = None,
    *,
    name: str | None = None,
    title: str = "Software Engineer",
    company: str | None = None,
    website: str | None = None,
) -> GeneratedResumePortfolio:
    """Load a local report and write synchronized résumé Markdown and HTML."""
    try:
        report = CareerReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ResumeError(f"could not read {report_path}: {exc.strerror or exc}") from exc
    except ValueError as exc:
        raise ResumeError(f"{report_path} is not a valid GitScope report: {exc}") from exc

    resolved_profile = profile or ResumeProfile.model_validate(
        {
            "name": name or report.identity.username,
            "title": title,
            "company": company or report.organization,
            "website": website,
        }
    )
    document = build_resume_document(report, resolved_profile)
    output_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output_directory, 0o700)
    markdown_path = output_directory / "resume.md"
    html_path = output_directory / "resume.html"
    _write_private_text(markdown_path, render_resume_markdown(document))
    _write_resume_html(document, html_path)
    return GeneratedResumePortfolio(
        document=document,
        markdown_path=markdown_path,
        html_path=html_path,
    )


def build_resume_document(report: CareerReport, profile: ResumeProfile) -> ResumeDocument:
    """Derive evidence-based résumé content without exposing repository names."""
    timeline = report.timeline
    commits = report.commit_summary
    pull_requests = report.pull_request_summary
    reviews = report.review_summary
    technologies = tuple(
        _RESUME_TECHNOLOGY_LABELS.get(item.name, item.name)
        for item in report.language_summary.contributed_languages
        if item.name.casefold() not in _RESUME_TECHNOLOGY_EXCLUSIONS
    )[:6]
    period = _period_label(timeline.first_contribution, timeline.last_contribution)
    technology_clause = (
        f" Primary contributed technologies include {_natural_list(technologies)}."
        if technologies
        else ""
    )
    summary = (
        f"{profile.title} at {profile.company} with a documented engineering contribution "
        f"history across {report.collection.repository_count:,} repositories in "
        f"{report.organization}. The collected record spans {period} and includes "
        f"{commits.total:,} authored commits, {pull_requests.total:,} authored pull requests, "
        f"and {reviews.total:,} submitted code reviews.{technology_clause}"
    )
    linkedin_summary = (
        f"I am a {profile.title} at {profile.company}. My GitScope contribution record spans "
        f"{period} across {report.collection.repository_count:,} repositories, covering "
        f"hands-on implementation, pull request delivery, and sustained peer review."
        f"{technology_clause} These figures document the collected scope and are not used as "
        "productivity scores."
    )
    highlights = _highlights(report, technologies, period)
    metrics = (
        ResumeMetric(
            label="Repositories",
            value=f"{report.collection.repository_count:,}",
            context="Selected organization scope",
        ),
        ResumeMetric(
            label="Authored commits",
            value=f"{commits.total:,}",
            context=f"Across {timeline.active_days:,} active days",
        ),
        ResumeMetric(
            label="Pull requests",
            value=f"{pull_requests.total:,}",
            context=f"{pull_requests.merged:,} merged",
        ),
        ResumeMetric(
            label="Code reviews",
            value=f"{reviews.total:,}",
            context=f"{reviews.approvals:,} approvals",
        ),
    )
    milestones = tuple(
        ResumeMilestone(label=item.label, occurred_at=item.occurred_at)
        for item in _select_milestones(timeline.milestones)
    )
    return ResumeDocument(
        profile=profile,
        github_username=report.identity.username,
        contribution_scope=report.organization,
        first_contribution=(
            timeline.first_contribution.date() if timeline.first_contribution else None
        ),
        last_contribution=(
            timeline.last_contribution.date() if timeline.last_contribution else None
        ),
        summary=summary,
        linkedin_summary=linkedin_summary,
        highlights=highlights,
        technologies=technologies,
        metrics=metrics,
        milestones=milestones,
        generated_at=report.collection.generated_at,
    )


def render_resume_markdown(document: ResumeDocument) -> str:
    """Render the structured résumé into portable Markdown."""
    profile = document.profile
    lines = [
        f"# {_escape_markdown(profile.name)}",
        "",
        f"**{_escape_markdown(profile.title)} · {_escape_markdown(profile.company)}**",
    ]
    if profile.website is not None:
        lines.extend(["", f"[Website]({profile.website})"])
    lines.extend(["", "## Professional summary", "", _escape_markdown(document.summary), ""])
    lines.extend(["## Selected contribution highlights", ""])
    lines.extend(f"- {_escape_markdown(item)}" for item in document.highlights)
    lines.extend(["", "## Primary technologies", ""])
    lines.append(
        ", ".join(_escape_markdown(item) for item in document.technologies) or "Not available"
    )
    lines.extend(["", "## Contribution evidence", ""])
    for metric in document.metrics:
        lines.append(
            f"- **{_escape_markdown(metric.label)}:** {metric.value} — "
            f"{_escape_markdown(metric.context)}"
        )
    lines.extend(["", "## Career milestones", ""])
    if document.milestones:
        lines.extend(
            f"- **{_format_date(item.occurred_at)}:** {_escape_markdown(item.label)}"
            for item in document.milestones
        )
    else:
        lines.append("No contribution milestones were available.")
    lines.extend(
        [
            "",
            "## LinkedIn summary",
            "",
            _escape_markdown(document.linkedin_summary),
            "",
            "---",
            "",
            (
                "Generated from a private GitScope report. Contribution counts document the "
                "collected scope and are not productivity metrics."
            ),
            "",
            (
                "**Made with care and** **❤️** **by** "
                "[**Manvendra Singh**](https://www.manvendrask.com/about)**.**"
            ),
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _highlights(
    report: CareerReport,
    technologies: tuple[str, ...],
    period: str,
) -> tuple[str, ...]:
    commits = report.commit_summary
    pull_requests = report.pull_request_summary
    reviews = report.review_summary
    highlights = [
        (
            f"Documented contributions across {report.collection.repository_count:,} "
            f"repositories from {period}, including {commits.total:,} authored commits."
        )
    ]
    if pull_requests.total:
        completed = pull_requests.merged + pull_requests.closed
        merge_context = (
            f", with a {pull_requests.merge_rate * 100:.1f}% merge rate across completed work"
            if completed and pull_requests.merge_rate is not None
            else ""
        )
        highlights.append(
            f"Authored {pull_requests.total:,} pull requests; {pull_requests.merged:,} merged"
            f"{merge_context}."
        )
    if reviews.total:
        highlights.append(
            f"Submitted {reviews.total:,} peer code reviews, including "
            f"{reviews.approvals:,} approvals and {reviews.changes_requested:,} requests "
            "for changes."
        )
    if technologies:
        highlights.append(
            f"Contributed primarily across {_natural_list(technologies)}, based on changed "
            "file types in the collected commit history."
        )
    if report.timeline.active_days:
        highlights.append(
            f"Recorded contribution activity on {report.timeline.active_days:,} distinct "
            f"days across a {report.timeline.career_span_days:,}-day span."
        )
    return tuple(highlights)


def _select_milestones(
    milestones: tuple[CareerMilestone, ...],
) -> tuple[CareerMilestone, ...]:
    selected = tuple(item for item in milestones if item.key in _MILESTONE_PRIORITY)
    return selected if selected else milestones[:8]


def _period_label(first: datetime | None, last: datetime | None) -> str:
    if first is None or last is None:
        return "the available report period"
    return f"{first:%B %Y} to {last:%B %Y}"


def _natural_list(values: tuple[str, ...]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _format_date(value: date | datetime) -> str:
    return f"{value:%b} {value.day}, {value:%Y}"


def _escape_markdown(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\\", "\\\\")
        .replace("*", "\\*")
        .replace("_", "\\_")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def _write_resume_html(document: ResumeDocument, path: Path) -> None:
    environment = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIRECTORY),
        autoescape=select_autoescape(("html", "xml")),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters["date"] = _format_date
    html = environment.get_template("resume.html").render(resume=document)
    _write_private_text(path, html)
    for asset in ("resume.css", "resume.js"):
        content = (_TEMPLATE_DIRECTORY / asset).read_text(encoding="utf-8")
        _write_private_text(path.parent / asset, content)


def _write_private_text(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)
