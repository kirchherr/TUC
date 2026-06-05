# RFC 0021: Release Provenance And SBOM

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1

## Summary

TUC adds a pre-publish release artifact workflow that builds Python
distributions, generates a CycloneDX SBOM, writes SHA-256 checksums, and creates
GitHub artifact attestations for provenance and the SBOM.

## Motivation

Compiler releases are high-trust artifacts. A compromised build can alter parser
behavior, IR validation, backend assignment, or runtime planning for every user.
Release controls should exist before TUC ships public packages, not after.

## Decision

Add `.github/workflows/release-artifacts.yml`.

The workflow runs on `workflow_dispatch` and `v*` tag pushes. It:

1. Installs TUC with development tooling.
2. Runs linting, typing, and tests.
3. Builds sdist and wheel artifacts with PyPA `build`.
4. Verifies that the built wheel imports.
5. Generates `dist/tuc.cdx.json`.
6. Generates `dist/SHA256SUMS`.
7. Uses `actions/attest@v4` for build provenance and SBOM attestations.
8. Uploads the artifacts as GitHub Actions artifacts.

The workflow does not publish to external package registries.

## Security Model

The release job has narrow write permissions:

- `id-token: write` for OIDC-backed signing.
- `attestations: write` for GitHub artifact attestations.

It does not receive package, repository-content write, or release-management
permissions.

The SBOM generator is repository-owned Python code. This avoids adding an
additional third-party action to the release trust boundary while TUC is still in
prototype phase.

## Limitations

- The SBOM currently covers direct runtime dependencies from `pyproject.toml`.
- The workflow does not prove reproducible builds.
- Release tags still need GitHub-side protection or maintainer-only creation.
- High-risk release actions are major-version pinned for the prototype and
  should be commit-SHA pinned before public package publication.

## Follow-Up

1. Add protected release tags.
2. Add PyPI trusted publishing only after maintainer approval policy is ready.
3. Extend SBOM coverage when native binaries, backend plugins, or containers are
   released.
4. Add reproducible build experiments once package contents stabilize.
