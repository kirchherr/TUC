# OCI Source Worker Release Provenance

TUC's protected release workflow now treats the source-ingestion worker as a
first-class release artifact. It builds a `linux/amd64` OCI Image Layout tar,
verifies it without extraction, generates a dedicated CycloneDX 1.6 SBOM,
writes SHA-256 checksums, and requests GitHub OIDC-backed provenance and SBOM
attestations. The same GitHub-hosted run then verifies the worker provenance
with `gh attestation verify` while binding the repository, signer repository,
signer workflow, source commit, source ref, OIDC issuer, predicate type, and
runner class.

The release toolchain is fixed to Buildx `v0.34.1` and digest-pinned BuildKit
`v0.30.0`. BuildKit starts with CDI disabled and without the setup action's
default `network.host` or `security.insecure` entitlements.

## Release Artifacts

- `tuc-source-ingestion-worker.oci.tar`
- `tuc-source-ingestion-worker.oci-verification.json`
- `tuc-source-ingestion-worker.cdx.json`
- `tuc-source-ingestion-worker.attestation-verification.json`
- `SHA256SUMS`

The archive verifier checks the OCI descriptor digest graph and enforces the
fixed `linux/amd64` platform, non-root `10001:10001` user, `/run/tuc` working
directory, isolated Python entrypoint, absence of a command override, and a
non-empty rootfs diff-ID chain. It also rejects unknown media types,
unreferenced archive members, and layer/rootfs cardinality drift.

The attestation-verification receipt is written only after the GitHub CLI
returns success. It binds the archive digest and size to the workflow run and
records the exact verification policy. Raw CLI output, the attestation bundle,
and archive bytes are omitted. The receipt is not self-authenticating and does
not grant execution permission. A `v*` push is recorded only as a release-tag
trigger; the receipt does not claim that repository ruleset protection was
independently verified. The runner-provided GitHub CLI version is recorded but
is not yet toolchain-pinned.

## Evidence

- Readiness example:
  `examples/oci_source_worker_release_provenance_readiness.py`
- Schema:
  `schemas/oci_source_worker_release_provenance_readiness_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/oci_source_worker_release_provenance_readiness_report.json`
- Release SBOM generator: `scripts/generate_source_worker_sbom.py`
- OCI archive verifier: `scripts/verify_source_worker_oci_archive.py`
- Attestation receipt writer:
  `scripts/write_github_attestation_verification_receipt.py`
- Receipt schema:
  `schemas/github_attestation_verification_receipt.v0.schema.json`
- RFC: [0290](../rfcs/0290-oci-source-worker-release-provenance.md)

## Remaining Boundary

The readiness report proves repository configuration and material binding. A
real workflow run will add same-run cryptographic verification evidence, but
the repository evidence does not assert that such a run has already completed.
It also does not assert independent consumer verification or publication.
Public registry publication, byte-identical reproducibility, production source
ingestion, and production sandbox claims remain blocked. Independent security
review is still required before any admitting parser surface can open.
