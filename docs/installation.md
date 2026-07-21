# Installation and first run

GitScope requires Python 3.13 or newer and Git on `PATH`. The recommended
installer is [uv](https://docs.astral.sh/uv/).

## Install a GitHub release

GitScope is distributed through GitHub Releases, not PyPI. Install the versioned
wheel as an isolated command-line tool:

```bash
uv tool install \
  https://github.com/CaptainOfFlyingDutchman/gitscope/releases/download/v0.3.0/gitscope-0.3.0-py3-none-any.whl
gitscope --version
gitscope doctor
```

The project named `gitscope` on PyPI is unrelated to this repository. Do not use
`uv tool install gitscope` to install this project.

Alternatively, install directly from the immutable Git tag:

```bash
uv tool install \
  'git+https://github.com/CaptainOfFlyingDutchman/gitscope.git@v0.3.0'
```

To upgrade later, install the new version's wheel URL with `--force`.

## Install a locally built wheel

Release candidates can be exercised without publishing them:

```bash
uv build
uv tool install dist/gitscope-0.3.0-py3-none-any.whl
gitscope --version
```

Use `--force` when replacing an existing local GitScope tool installation.

## Run from a source checkout

```bash
git clone https://github.com/CaptainOfFlyingDutchman/gitscope.git
cd gitscope
uv sync --all-groups
uv run gitscope --help
```

This is the contributor workflow. End users should prefer the versioned GitHub
release wheel.

## Configure GitHub access

GitScope reads `GITHUB_TOKEN` from the environment or a local `.env` file. The
token must be able to read every public or private repository included in the
analysis. Organization policy or SSO authorization may also apply to private
repositories.

```bash
cp .env.example .env
```

Then place the token in the untracked file:

```dotenv
GITHUB_TOKEN=your-token
```

Never commit `.env` or paste a token into an issue, report, or diagnostic log.
Use the shortest practical expiration and the least repository access needed
for the intended analysis.

## Define repository and identity scope

Copy the examples and keep the resulting files local:

```bash
cp .gitscope-repositories.example .gitscope-repositories
cp .gitscope-identities.example .gitscope-identities
```

`.gitscope-repositories` contains one `owner/name` repository per line. GitScope
only clones and analyzes repositories in this allowlist. The optional identity
file associates historical Git author names and email addresses with the target
user so renamed accounts and older commit identities remain attributable.

Both files are ignored by Git because they may reveal private information.

The allowlist is the recommended default. To deliberately include every
organization repository visible to the configured token, omit `--repos-file`
and run:

```bash
gitscope analyze \
  --org example-org \
  --user octocat \
  --all-repositories
```

`--all-repositories` cannot be combined with `--repos-file`. It can materially
increase API use and runtime. GitScope first inspects the resolved visible scope,
then creates full-history mirrors only for repositories with contribution
evidence. It displays both counts and stops before crossing its GraphQL
rate-limit reserve.

The commit prefilter uses the configured identity emails against each
repository's default-branch history. Pull-request, issue, and review evidence is
also included. A commit that exists only on an unmerged non-default branch and
has no associated contribution metadata cannot be identified without cloning
that repository; use the explicit allowlist when that edge case matters.

## Analyze and export

```bash
gitscope analyze --org example-org --user octocat
```

Use `--since` and `--until` to select inclusive UTC calendar dates:

```bash
gitscope analyze \
  --org example-org \
  --user octocat \
  --since 2024-01-01 \
  --until 2025-12-31
```

Either option may be used independently. Commits use their author timestamp,
pull requests and issues use their creation timestamp, and reviews use their
submission timestamp (falling back to creation when GitHub provides no
submission value). Pull-request and issue outcomes remain their current state.
Without date options, analysis covers the complete available history.

The default output is `career-report/`. Derived formats can later be regenerated
without GitHub access:

```bash
gitscope export all
gitscope resume --name "Example Engineer" --title "Principal Engineer"
```

## Local data and troubleshooting

GitScope stores full bare repository mirrors and GitHub response data under
`.gitscope/cache`. Reports, caches, allowlists, and logs can contain private
organization information and should not be published without review.

```bash
gitscope doctor
gitscope cache status
gitscope --verbose doctor
```

See [SECURITY.md](../SECURITY.md) for the complete data-handling and credential
guidance.
