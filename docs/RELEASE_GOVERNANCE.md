# Release Governance

This document defines the release governance controls TUC needs before any
public package publication.

TUC builds research artifacts and attestations. On 2026-11-13 the owner
approved disabling the historical tag publisher; workflow `289849327` was
verified as `disabled_manually`. The active manual research-candidate workflow
has no publisher. M2 requires a reviewed replacement, actual PyPI binding and
protected release approval. See the
[current candidate evidence](evidence/RESEARCH_CANDIDATE_8044760.md).

## Release Trigger

The active research build accepts manual `workflow_dispatch` on protected
`main`. It builds, attests and uploads artifacts without publication.
The disabled historical workflow definition retains these original triggers:

- Manual `workflow_dispatch` dry-runs that build, attest, and upload artifacts.
- `v*` tag pushes that build, attest, upload artifacts, and then wait for
  `pypi` environment approval before publishing.

Public publishing must not be triggered directly by ordinary pull requests,
unprotected branches, or user-controlled workflow inputs.

## Release Tag Ruleset

Create a GitHub repository tag ruleset before publishing packages:

- Target tag pattern: `v*`.
- Enforcement: active.
- Restrict tag creation to maintainers or release managers.
- Block tag updates and deletions.
- No standing administrator bypass. The installed immutable-tag ruleset has
  no bypass actors; the separate creation rule permits only `kirchherr`.

Release tags should use semantic version names such as:

```text
v0.1.0
v0.1.1
v1.0.0
```

The release workflow intentionally accepts `v*` so pre-release tags can be
tested later, but maintainers should keep the naming convention narrow.

## GitHub Environment For Publishing

TUC's publishing job uses a GitHub environment named:

```text
pypi
```

Required environment settings:

- Required reviewers enabled.
- No self-review for release approval.
- No administrator bypass of environment protection.
- Required reviewers `kirchherr` and `mailactiveblue-blip` (one eligible approval).
- Deployment branch/tag policy restricted to protected `main` and `v*` tags.
- No long-lived publishing secrets.

The publishing job is separate from the artifact-build job and receives only the
permissions it needs.

## PyPI Trusted Publishing

Use PyPI Trusted Publishing instead of stored PyPI API tokens.

The historical publisher policy binds to the following identifiers; its
workflow is now disabled and these lines do not establish the current PyPI
account-side configuration:

- Repository: `kirchherr/TUC`
- Workflow: `.github/workflows/release-artifacts.yml`
- Environment: `pypi`

Before M2, review the replacement publisher and verify its actual PyPI
repository/workflow/environment binding. The candidate build is not a
publisher and must not be granted publishing authority implicitly.

Do not add a PyPI token or password as a repository secret.

## Release Action Pinning

High-risk release actions are pinned to reviewed commit SHAs:

| Action | Reviewed Version | Commit SHA |
| --- | --- | --- |
| `actions/checkout` | `v6.0.2` | `de0fac2e4500dabe0009e67214ff5f5447ce83dd` |
| `actions/setup-python` | `v6.2.0` | `a309ff8b426b58ec0e2a45f0f869d46889d02405` |
| `docker/setup-buildx-action` | `v4.2.0` | `bb05f3f5519dd87d3ba754cc423b652a5edd6d2c` |
| `actions/attest` | `v4.1.0` | `59d89421af93a897026c735860bf21b6eb4f7b26` |
| `actions/upload-artifact` | `v7.0.1` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` |
| `actions/download-artifact` | `v8.0.1` | `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c` |
| `pypa/gh-action-pypi-publish` | `v1.14.0` | `cef221092ed1bacb1cc03d23a2d87d1d172e277b` |

The historical OCI builder toolchain is retained independently of the setup action:

| Tool | Version | Immutable Reference |
| --- | --- | --- |
| Docker Buildx | `v0.34.1` | setup action `version` input |
| Moby BuildKit | `v0.30.0` | `sha256:0168606be2315b7c807a03b3d8aa79beefdb31c98740cebdffdfeebf31190c9f` |

The active research candidate and PR image-check workflows retain Buildx
`v0.34.1` and use BuildKit `v0.35.0`, pinned to the verified Linux/amd64 manifest
`sha256:a521fc1fd903a46c611c733dd692548512232fba2e0386d6055846a903d05a71`.
The [security review](evidence/RESEARCH_CANDIDATE_8044760.md) records upstream
advisories affecting the historical version and the new registry identity.

BuildKit starts with `--cdi-disabled`; the workflow does not allow
`network.host`, `security.insecure`, or device entitlements.

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
- The release artifact bundle includes wheel, sdist, SBOM, Objective Delta
  reproduction kit and receipt, and `SHA256SUMS`.
- GitHub attestations are present for distributions and SBOM.
- GitHub attestations are present for the Objective Delta reproduction kit and
  receipt; neither is described as independent third-party evidence.
- At least one maintainer has reviewed release notes and artifact checksums.
- PyPI Trusted Publishing is configured with the `pypi` environment.

## Current Admin Dependency

GitHub rulesets, environments, and PyPI Trusted Publisher configuration are
admin-side settings. The repository workflow assumes those settings are active.
