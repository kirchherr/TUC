# Release Security

This document defines TUC's release artifact and publishing controls.

## Release Artifact Scope

The release workflow builds:

- Python source distribution.
- Python wheel.
- CycloneDX JSON SBOM.
- `linux/amd64` source-worker OCI Image Layout archive.
- Source-worker OCI verification report.
- Source-worker CycloneDX JSON SBOM.
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
- Only the artifact-build job receives `attestations: write`; its OIDC token is
  used only for GitHub artifact attestations.
- The PyPI publishing job receives a separate OIDC token and no attestation
  permission.
- The PyPI publishing job is isolated from artifact building and test execution.
- Release workflow actions are pinned to reviewed commit SHAs.
- Buildx is version-pinned and BuildKit is version- and digest-pinned with CDI
  disabled and no insecure build entitlement allowlist.
- The workflow uses GitHub OIDC-backed artifact attestations rather than stored
  signing secrets.
- The workflow builds artifacts from repository source and does not run dynamic
  plugin, backend, or generated-artifact execution.
- SBOM generation is repository-owned Python code, not a third-party action.
- The source-worker base image is digest-pinned, Python requirements are
  hash-locked, and the Docker build context is allowlisted.
- Repository-owned code verifies the OCI descriptor graph, platform, non-root
  identity, working directory, entrypoint, command policy, and rootfs digests
  before attestation.
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
gh attestation verify dist/tuc-source-ingestion-worker.oci.tar -R kirchherr/TUC
```

The checksum manifest can be checked locally:

```bash
cd dist
sha256sum -c SHA256SUMS
```

## SBOM Format

The SBOM format is CycloneDX JSON 1.6. The package SBOM describes the Python
project and direct runtime dependencies from `pyproject.toml`. The worker SBOM
separately binds its digest-pinned Python base image, hash-locked NumPy wheel,
Dockerfile, requirements, worker source, and target platform.

Future native backends, bundled binaries, generated compiler plugins, or runtime
artifacts must extend this SBOM model before release.

## Non-Goals

- Publishing the worker to a public container registry.
- Claiming an externally verified attestation before a protected release run is
  independently checked.
- Long-lived signing keys.
- Executing generated backend artifacts during release.
- Claiming reproducible builds.

See [OCI Source Worker Release Provenance](OCI_SOURCE_WORKER_RELEASE_PROVENANCE.md)
for the archive contract and remaining claim boundary.
