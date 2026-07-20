# GitScope

> Generate a beautiful, comprehensive engineering career report from GitHub organizations.

GitScope is a modern Python CLI that analyzes a developer's contributions across a GitHub organization and produces a professional report including commits, pull requests, code reviews, repository statistics, language breakdowns, timelines, charts, and an interactive HTML dashboard.

The project is intended to be open source and usable by anyone—not tied to a specific organization.

---

# Vision

Developers often lose access to company GitHub organizations after leaving.

GitScope exists to help developers preserve a snapshot of their engineering contributions before that access disappears.

The goal is **not** to measure productivity.

The goal is to create a professional engineering portfolio summarizing a developer's contributions over time.

GitScope should produce reports that developers can use for:

* Resume updates
* LinkedIn profiles
* Career portfolios
* Personal records
* Engineering reviews
* Promotion packets

---

# Design Philosophy

This project should feel like software written by an experienced engineer.

Do **not** optimize for generating code quickly.

Optimize for:

* readability
* maintainability
* correctness
* performance
* extensibility
* excellent UX

The codebase should be something that any experienced engineer would be comfortable maintaining.

---

# Technology Stack

Python 3.13

Package management:

* uv

Dependency management:

* pyproject.toml
* uv.lock

CLI:

* Typer

HTTP:

* httpx

GitHub APIs:

* GraphQL (preferred)
* REST (only when GraphQL is insufficient)

Git:

* GitPython or native git subprocesses where faster

Charts:

* Plotly

Templates:

* Jinja2

Data models:

* Pydantic

Testing:

* pytest

Linting:

* Ruff

Formatting:

* Ruff format

Type checking:

* mypy

---

# Development Workflow

Initialize project

```bash
uv init gitscope
```

Create virtual environment

```bash
uv venv
```

Run project

```bash
uv run gitscope --org my-org --user my-user
```

Run tests

```bash
uv run pytest
```

Lint

```bash
uv run ruff check
```

Format

```bash
uv run ruff format
```

---

# Project Structure

```
gitscope/

├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── LICENSE
├── .gitignore

├── gitscope/
│
│   ├── cli.py
│   ├── config.py
│   ├── cache.py
│   ├── logging.py
│
│   ├── github/
│   │     auth.py
│   │     graphql.py
│   │     rest.py
│   │     models.py
│   │
│   ├── git/
│   │     clone.py
│   │     commits.py
│   │     languages.py
│   │     stats.py
│   │
│   ├── analytics/
│   │     commits.py
│   │     prs.py
│   │     reviews.py
│   │     repositories.py
│   │     timeline.py
│   │
│   ├── charts/
│   │     activity.py
│   │     commits.py
│   │     reviews.py
│   │     languages.py
│   │     timeline.py
│   │
│   ├── report/
│   │     html.py
│   │     markdown.py
│   │     csv.py
│   │     json.py
│   │
│   ├── templates/
│   │     report.html
│   │     styles.css
│   │
│   └── models/
│
└── tests/
```

---

# Core Features

## Organization Analysis

Analyze every repository within a GitHub organization.

Collect:

* repositories contributed to
* commits
* pull requests
* pull request reviews
* issues
* discussion comments (future)
* repository metadata

---

## Commit Analytics

Generate:

* total commits
* commits per repository
* commits per year
* commits per month
* commits per weekday
* commits by hour
* first contribution
* last contribution

---

## Pull Request Analytics

Collect:

* PRs opened
* merged PRs
* closed PRs
* open PRs
* merge rate
* average merge time
* largest PRs
* longest-running PRs
* repositories with highest PR activity

---

## Review Analytics

Collect:

* total reviews
* approvals
* change requests
* comments
* reviews per repository
* reviews over time

Review statistics are especially valuable for senior and staff engineers because they represent engineering leadership rather than only authored code.

---

## Repository Analytics

For every repository collect:

* commit count
* PR count
* review count
* language
* stars
* forks
* visibility
* default branch

---

## Language Analytics

Generate language distribution based on repositories and contributions.

Example:

* TypeScript
* Go
* CSS
* HTML
* YAML
* JSON
* Shell

---

## Timeline

Generate milestones such as:

* first contribution
* 100th commit
* 500th commit
* first merged PR
* 100th PR
* last contribution

---

## Code Statistics

Using local Git repositories calculate:

* lines added
* lines removed
* files modified
* file extensions
* approximate language statistics

Note:

Lines of code should never be presented as a productivity metric.

---

# Outputs

GitScope should generate multiple formats.

```
career-report/

report.html
report.md
report.json
report.csv

charts/
```

---

## HTML Dashboard

This is the flagship output.

Should contain:

* overview cards
* repository rankings
* contribution timeline
* charts
* language distribution
* contribution heatmap
* tables
* responsive layout
* printable styling

The dashboard should feel polished and modern.

---

## Markdown Report

A lightweight report suitable for GitHub or personal archives.

---

## CSV Export

Raw data suitable for Excel or further analysis.

---

## JSON Export

Machine-readable output for integrations.

---

# Resume Mode

Generate synchronized Markdown and HTML contribution résumés from an existing
`report.json` without making GitHub API requests:

```bash
gitscope resume \
  --name "Manvendra Singh" \
  --title "Staff Engineer" \
  --company "Josys" \
  --site "https://example.com/about"
```

By default, GitScope reads `career-report/report.json` and writes:

```text
career-report/
├── resume.md
├── resume.html
├── resume.css
└── resume.js
```

The HTML résumé is responsive, supports light and dark themes, and includes
A4 print styling for saving as PDF. Generated content is deterministic and
evidence-based. Private repository names are not included, and contribution
counts are presented as documentation rather than productivity scores.

When profile options are omitted, the GitHub username, a neutral software
engineer title, and the report organization are used as defaults.

The résumé includes a concise engineering summary suitable for résumés or
LinkedIn.

Example:

> Staff Software Engineer contributing across 41 repositories with 2,314 commits, 487 pull requests, and 1,142 code reviews. Primary technologies include TypeScript, Go, React, and CSS, with significant contributions to frontend architecture, shared libraries, and engineering standards.

---

# Performance Goals

GitScope should remain fast even for organizations with many repositories.

Use:

* concurrent repository processing
* caching
* incremental updates
* GraphQL batching

GitScope intentionally uses cached **full bare repository mirrors**, not shallow
clones. Complete Git history is required to produce accurate lifetime commit,
timeline, identity-alias, and code-change statistics. A shallow clone would make
those results incomplete or dependent on an arbitrary depth.

The initial mirror can therefore require more time and disk space. Subsequent
runs reuse the private local mirror, and `--refresh` performs an incremental
fetch rather than cloning the repository again.

Avoid unnecessary API requests.

Respect GitHub rate limits.

---

# Caching

Cache:

* repository metadata
* GraphQL responses
* cloned repositories
* computed analytics

Store cache under:

```
.gitscope/cache/
```

Subsequent executions should be significantly faster.

---

# Error Handling

The application should:

* continue processing if a repository fails
* display friendly error messages
* log detailed diagnostics
* retry transient API failures
* detect rate limiting
* gracefully recover where possible

Never crash because of a single repository.

---

# Quality Standards

Every module should:

* include type hints
* include documentation
* have unit tests
* follow clean architecture principles
* avoid duplication
* keep functions focused and small

Avoid giant utility files.

Avoid global state.

Prefer composition over inheritance.

---

# Coding Standards

Prefer:

* explicit names
* dataclasses or Pydantic models
* dependency injection where appropriate
* immutable data where practical
* small, testable modules

Keep cyclomatic complexity low.

Avoid premature abstraction.

---

# CLI Experience

The CLI should feel polished.

Examples:

```
gitscope analyze --org josys-src --user octocat

gitscope resume

gitscope export html

gitscope export markdown
```

Use:

* progress bars
* colored output
* clear summaries
* helpful error messages

---

# Remaining 0.1.0 Milestones

The remaining milestones for the first public release are:

1. **Advanced Pull Request Analytics**
   * merge-time statistics
   * largest and longest-running pull requests
   * open pull-request age
   * pull-request activity rankings and visualizations
2. **Issue Contributions**
   * authored issue collection
   * issue states, timelines, and repository summaries
3. **Offline Export and CLI UX**
   * regenerate individual outputs from an existing `report.json`
   * `gitscope export` commands
   * improved progress and terminal summaries
4. **Logging, Cache Management, and Diagnostics**
   * sanitized diagnostic logging
   * cache inspection and lifecycle commands
   * verbose troubleshooting mode
5. **CI, Documentation, and Release Readiness**
   * automated tests, linting, typing, and package builds
   * installation, contribution, security, and architecture documentation
   * installed-wheel verification
6. **GitScope 0.1.0 Release**
   * final package metadata and version verification
   * `uv tool install` readiness
   * first public release

---

# Future Roadmap

The following ideas are explicitly deferred beyond the current `0.1.0` plan.
They are not being implemented as part of the milestones above:

* GitLab support
* Azure DevOps support
* Bitbucket support
* Team comparison reports
* Multi-organization reports
* PDF export
* Interactive web application
* Docker image
* GitHub Action
* Homebrew installation
* Plugin architecture

---

# Non-Goals

GitScope is **not** intended to:

* rank developers
* score productivity
* compare engineers
* gamify contributions
* encourage unhealthy metrics

The focus is on documentation and visualization of engineering work.

---

# Success Criteria

A successful GitScope release should be something an experienced engineer would happily install with:

```
uv tool install gitscope
```

and immediately use to generate a polished report for any GitHub organization they have access to.

The project should prioritize quality over quantity, clarity over cleverness, and long-term maintainability over short-term implementation speed.

This README should give Codex (or any other coding agent) enough context to keep the implementation aligned with the project's goals and maintain a consistently high engineering standard.
