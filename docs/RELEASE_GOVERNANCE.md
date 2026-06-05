# Release Governance

This document defines the release governance controls TUC needs before any
public package publication.

TUC currently builds release artifacts and attestations, but it does not publish
to PyPI, GHCR, or any other external registry.

## Release Trigger

Release artifact builds may run through:

- Manual `workflow_dispatch` dry-runs.
- `v*` tag pushes.

Public publishing must not be triggered directly by ordinary pull requests,
unprotected branches, or user-controlled workflow inputs.

## Release Tag Ruleset

Create a GitHub repository tag ruleset before publishing packages:

- Target tag pattern: `v*`.
- Enforcement: active.
- Restrict tag creation to maintainers or release managers.
- Block tag updates and deletions.
- Allow administrator bypass only for documented incident recovery.

Release tags should use semantic version names such as:

```text
v0.1.0
v0.1.1
v1.0.0
```

The release workflow intentionally accepts `v*` so pre-release tags can be
tested later, but maintainers should keep the naming convention narrow.

## GitHub Environment For Publishing

If TUC adds a publishing job, create a GitHub environment named:

```text
pypi
```

Required environment settings:

- Required reviewers enabled.
- No self-review for release approval.
- Deployment branch/tag policy restricted to protected branches and `v*` tags.
- No long-lived publishing secrets.

The publishing job must be separate from the artifact-build job and must receive
only the permissions it needs.

## PyPI Trusted Publishing

Use PyPI Trusted Publishing instead of stored PyPI API tokens.

The PyPI publisher configuration must bind to:

- Repository: `kirchherr/TUC`
- Workflow: `.github/workflows/release-artifacts.yml` or a later dedicated
  publishing workflow.
- Environment: `pypi`

Do not add a PyPI token or password as a repository secret.

## Release Action Pinning

High-risk release actions are pinned to reviewed commit SHAs:

| Action | Reviewed Version | Commit SHA |
| --- | --- | --- |
| `actions/checkout` | `v6.0.2` | `de0fac2e4500dabe0009e67214ff5f5447ce83dd` |
| `actions/setup-python` | `v6.2.0` | `a309ff8b426b58ec0e2a45f0f869d46889d02405` |
| `actions/attest` | `v4.1.0` | `59d89421af93a897026c735860bf21b6eb4f7b26` |
| `actions/upload-artifact` | `v7.0.1` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` |

When updating a release action:

1. Review the upstream release notes.
2. Resolve the exact tag commit with `git ls-remote`.
3. Update the workflow SHA and this table together.
4. Run the release workflow in dry-run mode before publishing.

## Publishing Approval Checklist

Before a public release:

- Branch protection is active on `main`.
- The `v*` tag ruleset is active.
- The release workflow has completed successfully.
- The release artifact bundle includes wheel, sdist, SBOM, and `SHA256SUMS`.
- GitHub attestations are present for distributions and SBOM.
- At least one maintainer has reviewed release notes and artifact checksums.
- PyPI Trusted Publishing is configured with the `pypi` environment.

## Current Limitation

This repository can document and test release workflow policy, but GitHub
rulesets, environments, and PyPI Trusted Publisher configuration must be applied
by a repository or PyPI project administrator.
