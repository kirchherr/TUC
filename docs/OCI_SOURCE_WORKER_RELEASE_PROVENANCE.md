# OCI Source Worker Release Provenance

TUC's protected release workflow now treats the source-ingestion worker as a
first-class release artifact. It builds a `linux/amd64` OCI Image Layout tar,
verifies it without extraction, generates a dedicated CycloneDX 1.6 SBOM,
writes SHA-256 checksums, and requests GitHub OIDC-backed provenance and SBOM
attestations.

The release toolchain is fixed to Buildx `v0.34.1` and digest-pinned BuildKit
`v0.30.0`. BuildKit starts with CDI disabled and without the setup action's
default `network.host` or `security.insecure` entitlements.

## Release Artifacts

- `tuc-source-ingestion-worker.oci.tar`
- `tuc-source-ingestion-worker.oci-verification.json`
- `tuc-source-ingestion-worker.cdx.json`
- `SHA256SUMS`

The archive verifier checks the OCI descriptor digest graph and enforces the
fixed `linux/amd64` platform, non-root `10001:10001` user, `/run/tuc` working
directory, isolated Python entrypoint, absence of a command override, and a
non-empty rootfs diff-ID chain. It also rejects unknown media types,
unreferenced archive members, and layer/rootfs cardinality drift.

## Evidence

- Readiness example:
  `examples/oci_source_worker_release_provenance_readiness.py`
- Schema:
  `schemas/oci_source_worker_release_provenance_readiness_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/oci_source_worker_release_provenance_readiness_report.json`
- Release SBOM generator: `scripts/generate_source_worker_sbom.py`
- OCI archive verifier: `scripts/verify_source_worker_oci_archive.py`
- RFC: [0290](../rfcs/0290-oci-source-worker-release-provenance.md)

## Remaining Boundary

The readiness report proves repository configuration and material binding. It
does not assert that a release artifact has already been published or that an
external verifier has accepted its GitHub attestation. Public registry
publication, byte-identical reproducibility, production source ingestion, and
production sandbox claims remain blocked. Independent security review is still
required before any admitting parser surface can open.
