# RFC 0023: PyPI Trusted Publish Job

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1

## Summary

TUC adds an isolated PyPI publishing job to the release-artifact workflow. The
job publishes only on protected `v*` tag pushes, waits for the `pypi` GitHub
environment, and authenticates to PyPI through Trusted Publishing OIDC.

## Motivation

TUC now has release artifacts, attestations, tag protection, a GitHub publishing
environment, and a PyPI Trusted Publisher. The repository needs a matching
workflow job that uses those controls without introducing long-lived PyPI
tokens.

## Decision

Extend `.github/workflows/release-artifacts.yml` with a `publish` job.

The job:

- Depends on the artifact-build job.
- Runs only for `push` events on `refs/tags/v*`.
- Uses the `pypi` environment.
- Grants only `id-token: write`.
- Downloads the release artifact bundle.
- Copies only wheel and source distribution files into `dist/`.
- Publishes through `pypa/gh-action-pypi-publish`.

Manual `workflow_dispatch` runs remain dry-runs and do not publish.

## Security Model

The publishing job does not build, test, attest, or execute generated compiler
artifacts. It only retrieves artifacts from the same workflow run and publishes
Python distributions after environment approval.

No PyPI token, password, or long-lived publishing secret is added.

The PyPA publishing action and download action are pinned to reviewed commit
SHAs, and the release-action pinning test covers them.

## Limitations

- PyPI package name availability and ownership remain external to the repo.
- Publishing is only as strong as the protected tag and `pypi` environment
  configuration.
- The first release should still be reviewed manually before creating the tag.

## Follow-Up

1. Run a manual release-artifact dry-run before the first tag.
2. Verify PyPI Trusted Publisher project binding after the first publish.
3. Add release-note templates and package verification instructions.
