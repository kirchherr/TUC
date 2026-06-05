# Release Security

TUC does not publish packages yet. This document defines the minimum release
artifact controls that must be in place before the first public package release.

## Release Artifact Scope

The release workflow builds:

- Python source distribution.
- Python wheel.
- CycloneDX JSON SBOM.
- SHA-256 checksum manifest.
- GitHub artifact attestations for build provenance and the SBOM.

The workflow uploads these files as GitHub Actions artifacts. It does not publish
to PyPI, GHCR, or any external package registry.

## Trust Boundary

Release artifacts change TUC's downstream trust boundary because users may run
compiler code from those artifacts. A release build must therefore be treated as
more sensitive than ordinary CI.

Current controls:

- Release workflow permissions are least-privilege by default.
- Only the release job receives `id-token: write` and `attestations: write`.
- The workflow uses GitHub OIDC-backed artifact attestations rather than stored
  signing secrets.
- The workflow builds artifacts from repository source and does not run dynamic
  plugin, backend, or generated-artifact execution.
- SBOM generation is repository-owned Python code, not a third-party action.
- The workflow can run manually for dry-runs and automatically for `v*` tags.

## Required Before Publishing

Before TUC publishes to any registry:

1. Protect release tags or restrict tag creation to maintainers.
2. Pin high-risk release actions to reviewed commit SHAs.
3. Add a release approval process for public package publication.
4. Decide whether package publication uses PyPI trusted publishing or another
   OIDC-based mechanism.
5. Document the package verification command in the release notes.

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

## Non-Goals For This Slice

- Publishing to PyPI.
- Publishing container images.
- Long-lived signing keys.
- Executing generated backend artifacts during release.
- Claiming reproducible builds.
