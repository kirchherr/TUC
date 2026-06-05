# Release Security

This document defines TUC's release artifact and publishing controls.

## Release Artifact Scope

The release workflow builds:

- Python source distribution.
- Python wheel.
- CycloneDX JSON SBOM.
- SHA-256 checksum manifest.
- GitHub artifact attestations for build provenance and the SBOM.

The workflow uploads these files as GitHub Actions artifacts. On protected `v*`
tag pushes, it can also publish wheel and source distribution files to PyPI
after `pypi` environment approval.

## Trust Boundary

Release artifacts change TUC's downstream trust boundary because users may run
compiler code from those artifacts. A release build must therefore be treated as
more sensitive than ordinary CI.

Current controls:

- Release workflow permissions are least-privilege by default.
- Only the artifact-build job receives `attestations: write`.
- Only the PyPI publishing job receives `id-token: write`.
- The PyPI publishing job is isolated from artifact building and test execution.
- Release workflow actions are pinned to reviewed commit SHAs.
- The workflow uses GitHub OIDC-backed artifact attestations rather than stored
  signing secrets.
- The workflow builds artifacts from repository source and does not run dynamic
  plugin, backend, or generated-artifact execution.
- SBOM generation is repository-owned Python code, not a third-party action.
- Manual workflow runs are dry-runs. Publishing is restricted to `v*` tag pushes.

## Required For Publishing

Before TUC publishes to PyPI:

1. Protect release tags or restrict tag creation to maintainers.
2. Require `pypi` environment approval.
3. Use PyPI Trusted Publishing through OIDC.
4. Document the package verification command in the release notes.

See [Release governance](RELEASE_GOVERNANCE.md) for the required GitHub tag
ruleset and publishing-environment policy.

## Verification

Consumers or maintainers can verify GitHub artifact attestations with the GitHub
CLI once release artifacts are produced:

```bash
gh attestation verify dist/tuc-0.1.0-py3-none-any.whl -R kirchherr/TUC
gh attestation verify dist/tuc-0.1.0.tar.gz -R kirchherr/TUC
```

The checksum manifest can be checked locally:

```bash
cd dist
sha256sum -c SHA256SUMS
```

## SBOM Format

The SBOM format is CycloneDX JSON 1.6. The current SBOM describes the Python
project package and direct runtime dependencies from `pyproject.toml`.

Future native backends, bundled binaries, generated compiler plugins, or runtime
artifacts must extend this SBOM model before release.

## Non-Goals

- Publishing container images.
- Long-lived signing keys.
- Executing generated backend artifacts during release.
- Claiming reproducible builds.
