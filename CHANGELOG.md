# Changelog

All notable changes to GitScope are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.1]: https://github.com/CaptainOfFlyingDutchman/gitscope/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/CaptainOfFlyingDutchman/gitscope/releases/tag/v0.1.0
