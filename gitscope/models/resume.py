"""Structured models shared by résumé Markdown and HTML outputs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class ResumeModel(BaseModel):
    """Immutable base for résumé-domain models."""

    model_config = ConfigDict(frozen=True)


class ResumeProfile(ResumeModel):
    """User-supplied professional identity fields."""

    name: str = Field(min_length=1)
    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    website: AnyHttpUrl | None = None


class ResumeMetric(ResumeModel):
    """Compact evidence displayed in the résumé sidebar."""

    label: str
    value: str
    context: str


class ResumeMilestone(ResumeModel):
    """Repository-neutral career milestone."""

    label: str
    occurred_at: datetime


class ResumeDocument(ResumeModel):
    """Stable structured content rendered into synchronized résumé outputs."""

    schema_version: Literal["1.0"] = "1.0"
    profile: ResumeProfile
    github_username: str
    contribution_scope: str
    first_contribution: date | None
    last_contribution: date | None
    summary: str
    linkedin_summary: str
    highlights: tuple[str, ...]
    technologies: tuple[str, ...]
    metrics: tuple[ResumeMetric, ...]
    milestones: tuple[ResumeMilestone, ...]
    generated_at: datetime
