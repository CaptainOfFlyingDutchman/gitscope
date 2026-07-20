# GitScope architecture

## Purpose and boundaries

GitScope is a local Python CLI that converts an explicitly scoped set of GitHub
contributions into a versioned career report and derived presentation formats.
It documents engineering work; it does not rank engineers, score productivity,
or compare people.

The main architectural boundary is `report.json`. Collection code produces this
versioned contract. HTML, Markdown, CSV, chart, and résumé generators consume it
without requiring GitHub, Git repositories, credentials, or cache state.

## Data flow

```text
CLI and local configuration
        │
        ├── GitHub API collection ── GraphQL / REST response cache
        │
        ├── Repository allowlist ── full bare Git mirrors
        │                                │
        └── Historical identities ──────┘
                         │
                  Typed source models
                         │
             Analytics and timeline builders
                         │
                Versioned CareerReport
                         │
                    report.json
                         │
        ┌──────────┬─────┴─────┬──────────┬────────┐
        HTML    Markdown      CSV       Charts   Résumé
```

## Module responsibilities

### CLI and configuration

- `gitscope/cli.py` defines commands, user-facing progress, summaries, and exit
  behavior.
- `gitscope/config.py` validates runtime settings and retrieves the token from
  the environment.
- `gitscope/repository_scope.py` validates the private repository allowlist.
- `gitscope/diagnostics.py`, `gitscope/cache.py`, and `gitscope/logging.py`
  provide local diagnostics, bounded cache operations, and sanitized logging.

The CLI coordinates components but should not contain collection or analytics
business logic.

### GitHub metadata collection

`gitscope/github/` owns authenticated HTTP behavior and GitHub source models.
GraphQL is preferred for batched contribution metadata; REST is used where the
required data is unavailable or impractical through GraphQL. The HTTP layer owns
retry, rate-limit, pagination, and response-cache behavior.

API models remain separate from the report contract so upstream response changes
do not leak directly into persisted reports.

### Git history collection

`gitscope/git/` owns authenticated cloning, full bare mirror updates, commit
enumeration, historical identity matching, and contributed-file statistics.
Full history is intentional: shallow clones would make lifetime counts and alias
matching incomplete.

Only repositories in `.gitscope-repositories` enter this pipeline. Concurrency
is bounded by the CLI option, and individual repository failures are represented
as warnings rather than silently changing successful results.

### Analytics

`gitscope/analytics/` converts collected source records into deterministic
summaries for commits, pull requests, reviews, issues, repositories, and career
timelines. Analytics functions should remain side-effect-free where practical
and accept typed inputs.

### Report contract

`gitscope/models/report.py` defines the immutable Pydantic `CareerReport`. The
`schema_version` field is a compatibility contract, not the package version.
Readers validate JSON before producing outputs, and compatibility tests protect
supported earlier schemas.

Adding a required field, changing semantics, or removing compatibility requires
an intentional schema migration. Additive fields should have safe defaults when
older reports remain supported.

### Presentation and offline export

- `gitscope/charts/` contains reusable Plotly figure builders and the standalone
  chart bundle.
- `gitscope/report/` writes JSON, HTML, Markdown, CSV, and résumé outputs.
- `gitscope/templates/` contains package data required at runtime.

Offline exporters read only a validated `report.json`. They must remain
deterministic and must not call GitHub, inspect Git repositories, or require a
token. Plotly is copied locally so HTML outputs remain portable and offline.

## Storage layout

```text
.gitscope/
├── cache/
│   ├── graphql/          cached GitHub responses
│   └── repositories/    full bare Git mirrors
└── logs/
    └── gitscope.log     private rotating diagnostics

career-report/           generated private outputs
```

Cache clearing is allowlisted to the two cache subdirectories. It never removes
the `.gitscope` root, logs, reports, configuration, repository allowlist, or
identity file.

## Privacy and security boundaries

- Secrets enter through environment configuration and are not report fields.
- The allowlist bounds repository cloning and analysis.
- Logs store operational aggregates and exception types; their formatter redacts
  known credential forms.
- Diagnostic and cache commands avoid displaying payloads or private repository
  names.
- Generated outputs and caches are private local data even when credentials are
  absent from them.
- CI uses only synthetic fixtures and does not require repository or organization
  secrets.

See [SECURITY.md](../SECURITY.md) for operational guidance.

## Packaging and release verification

Hatchling builds the wheel and source distribution. Runtime templates are
explicit package contents. CI verifies the archive for required files and
forbidden private/generated paths, installs the wheel into an isolated virtual
environment, and invokes the installed `gitscope` entry point from outside the
source tree.

The smoke test regenerates all offline outputs and the résumé from a synthetic
fixture. This verifies the console entry point, declared runtime dependencies,
template packaging, Plotly runtime export, and report compatibility together.
