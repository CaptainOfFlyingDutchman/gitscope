# Contributing to GitScope

Thank you for improving GitScope. Contributions should preserve its central
principles: accurate career documentation, strong privacy boundaries, and no
developer ranking or productivity scoring.

## Development setup

Prerequisites:

- Python 3.13 or newer
- Git
- [uv](https://docs.astral.sh/uv/)

Clone the repository and install the locked development environment:

```bash
git clone https://github.com/CaptainOfFlyingDutchman/gitscope.git
cd gitscope
uv sync --all-groups
```

No GitHub token is needed for the unit test suite or offline export work.

## Required checks

Run these before opening a pull request:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy gitscope scripts
uv run pytest
```

Use `uv run ruff format .` to apply formatting. CI repeats every check using the
committed lockfile.

For packaging changes, also run:

```bash
uv build
uv run python scripts/verify_wheel.py dist/*.whl --sdist dist/*.tar.gz
```

The installed-wheel smoke test is run automatically in CI. It installs the
wheel outside the source tree and exercises diagnostics, all offline exports,
charts, and résumé generation.

## Dependency changes

Add runtime dependencies with `uv add` and development dependencies with
`uv add --dev`. Commit both `pyproject.toml` and `uv.lock`. Avoid dependencies
when the standard library or an existing package is sufficient.

## Tests and fixtures

- Add or update focused tests for behavior changes.
- Keep tests deterministic and independent of GitHub credentials or network
  access unless the HTTP layer is explicitly mocked.
- Never copy real organization payloads, repository names, tokens, logs, caches,
  or personal career reports into fixtures.
- Use synthetic identities and repositories such as `octocat` and
  `example-org/example-repo`.
- Preserve support for older documented report schemas when changing models.

## Code and architecture expectations

- Keep strict type annotations and focused functions.
- Preserve module boundaries described in
  [docs/architecture.md](docs/architecture.md).
- Treat `report.json` as a versioned public contract. Schema changes require
  compatibility tests and an intentional schema-version decision.
- Avoid metrics or language that rank engineers or equate activity counts with
  productivity.
- Never make offline export commands depend on a token, network, Git checkout,
  or cache.

## Pull requests

Explain the user-visible outcome, important design choices, tests performed, and
privacy or compatibility implications. Keep unrelated changes out of the same
pull request. CI must pass before merge.

Security vulnerabilities should not be reported through a public issue. Follow
[SECURITY.md](SECURITY.md) instead.
