# Maintainer release procedure

GitScope is distributed through GitHub Releases rather than PyPI. Pushing a
validated semantic-version tag is the only publication trigger.

## Prerequisites

- Work from `main` with no uncommitted changes.
- Confirm local `main` matches `origin/main`.
- Confirm the CI workflow is green for the release-preparation commit.
- Confirm `pyproject.toml` and `gitscope/__init__.py` contain the intended version.
- Add a dated entry to `CHANGELOG.md`.
- Add `docs/releases/v<version>.md`.
- Never reuse or move a tag associated with a published release.

Run the same validation used by release automation:

```bash
uv run python scripts/validate_release.py --tag v0.2.1
uv run ruff check .
uv run ruff format --check .
uv run mypy gitscope scripts
uv run pytest
```

## Trigger the release

Only after the release-preparation commit is pushed and CI succeeds, create and
push the annotated tag:

```bash
git tag -a v0.2.1 -m "GitScope 0.2.1"
git push origin v0.2.1
```

The second command publishes the tag and triggers `.github/workflows/release.yml`.
An ordinary commit or branch push does not start the release workflow.

## Automated release work

The workflow validates that the tag, package metadata, changelog, and release
notes agree. It then repeats linting, formatting, typing, and tests; builds the
wheel and source distribution without local uv sources; inspects distribution
contents; installs and smoke-tests the wheel outside the source tree; generates
`SHA256SUMS`; and creates the GitHub release with all three assets.

If any validation fails, the workflow does not create a GitHub release. Diagnose
the failure before taking further tag action. Never move a tag after a public
release exists; make corrections in the next patch release instead.

## Verify publication

```bash
gh release view v0.2.1
gh release download v0.2.1 --dir release-assets
```

Verify the checksum manifest from the download directory:

```bash
cd release-assets
shasum -a 256 -c SHA256SUMS
```

Finally, install the public wheel URL in an isolated uv tool environment and run
`gitscope --version` and `gitscope doctor`.
