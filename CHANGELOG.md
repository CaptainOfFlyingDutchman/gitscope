# Changelog

All notable changes to GitScope are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-07-21

### Fixed

- Plotly hover labels now use opaque, high-contrast backgrounds, borders, and text in both light and dark dashboard themes.
- Reports with no authored issues now show an explicit Issue Outcomes empty state instead of silently omitting the chart card.

## [0.2.0] - 2026-07-21

### Added

- An explicit `--all-repositories` analysis mode for every organization repository visible to the configured GitHub token.
- Resolved visible/private and contribution-selected repository counts before full-history Git analysis begins.

### Changed

- Pull-request, issue, and review collectors now enforce the GraphQL reserve before moving to another repository as well as during pagination.
- All-repositories mode now prefilters with contribution metadata and batched default-branch commit presence, avoiding mirrors for repositories without contribution evidence.
- Organization-wide contribution searches replace per-repository searches in all-repositories mode, reducing API calls and runtime.
- HTML and Markdown contribution tables now omit repositories with no collected commits, pull requests, issues, or reviews while retaining the full scope in report metadata.

### Security

- The private repository allowlist remains the default; `--all-repositories` cannot be combined with `--repos-file`.

## [0.1.1] - 2026-07-21

### Added

- A packaged GitScope SVG favicon for the offline dashboard, contribution résumé, and every standalone chart page.

### Changed

- Offline HTML exporters now copy the favicon alongside their other private, portable assets.

## [0.1.0] - 2026-07-21

### Added

- Scoped contribution collection for commits, pull requests, reviews, and issues.
- Historical Git identity matching across renamed accounts and author aliases.
- Full-history bare repository mirrors with contribution-based language and file analytics.
- Versioned JSON report schema with HTML, Markdown, CSV, and standalone Plotly outputs.
- Advanced pull-request lifecycle, scale, repository, and merge-time analytics.
- Issue state, repository, and timeline analytics.
- Responsive contribution résumé with light, dark, and print-friendly presentation.
- Offline export commands that regenerate outputs without GitHub or Git access.
- Private rotating logs, credential redaction, bounded cache management, and local diagnostics.
- Automated linting, formatting, strict typing, testing, distribution inspection, and installed-wheel smoke tests.
- GitHub-only release automation with verified artifacts and SHA-256 checksums.

### Security

- Repository allowlists bound private cloning and analysis scope.
- Generated reports, caches, credentials, identity files, and repository lists are ignored by Git.
- Distribution verification rejects private state, generated reports, and missing runtime templates.

[0.2.1]: https://github.com/CaptainOfFlyingDutchman/gitscope/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/CaptainOfFlyingDutchman/gitscope/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/CaptainOfFlyingDutchman/gitscope/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/CaptainOfFlyingDutchman/gitscope/releases/tag/v0.1.0
