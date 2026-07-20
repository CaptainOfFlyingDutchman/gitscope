# Security policy

GitScope handles GitHub credentials and may process private repository metadata
and source history. Security and privacy defects are treated as product defects.

## Supported versions

Before the first stable release, security fixes are applied to the latest code
on `main`. After releases begin, this table will identify supported release
lines explicitly.

| Version | Supported |
| --- | --- |
| Latest `0.1.x` release | Yes |
| Older or unreleased revisions | No |

## Report a vulnerability

Do not open a public issue containing vulnerability details, credentials,
private repository names, cached payloads, or generated reports.

Use GitHub's private vulnerability reporting for this repository:

<https://github.com/CaptainOfFlyingDutchman/gitscope/security/advisories/new>

Include a concise description, affected version or commit, reproduction steps,
impact, and any suggested mitigation. Use synthetic data and redact secrets.

## Credential model

- GitScope reads `GITHUB_TOKEN` from the process environment or an untracked
  `.env` file.
- Tokens are used for GitHub API requests and authenticated Git repository
  access; they are never written into `report.json`.
- Diagnostic logging redacts the configured token, known GitHub token shapes,
  authorization headers, and URL passwords.
- Redaction is defense in depth, not permission to log arbitrary secrets.
- Use least-privilege repository access, a practical expiration, and any SSO or
  organization authorization required by the repositories in scope.
- Revoke and replace a token immediately if it may have been exposed.

## Local private data

The following paths are intentionally ignored by Git and should be treated as
private:

```text
.env
.gitscope-repositories
.gitscope-identities
.gitscope/cache/
.gitscope/logs/
career-report/
```

The repository cache contains full bare mirrors. Generated reports can contain
repository names, URLs, contribution metadata, pull-request and issue titles,
and aggregate code-change information. File permissions reduce accidental local
access but do not encrypt data at rest.

Review generated files before sharing them. Use operating-system disk encryption
where appropriate, and delete local data according to your organization’s
policies.

## Safe cleanup

Inspect or clear regenerable cache sections with:

```bash
gitscope cache status
gitscope cache clear graphql
gitscope cache clear repositories
gitscope cache clear all
```

These commands do not delete reports, configuration, logs, allowlists, or
identity files. Remove those separately only after verifying the exact path and
retention requirements.

## Release safeguards

CI builds the wheel and source distribution from tracked project files. The
wheel verifier rejects private configuration names, generated reports, cache
directories, bytecode, and missing runtime templates. A clean-environment smoke
test then exercises the installed CLI and offline generators.
