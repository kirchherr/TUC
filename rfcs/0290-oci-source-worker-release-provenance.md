# RFC 0290: OCI Source Worker Release Provenance

Status: Accepted for research release artifacts

## Decision

TUC will build the source-ingestion worker as an OCI Image Layout archive in
the protected release workflow. Before attestation, repository-owned code must
validate the archive descriptor graph and the fixed runtime configuration. The
workflow then generates a worker-specific CycloneDX SBOM, writes checksums,
and uses GitHub OIDC artifact attestations for both provenance and SBOM.

## Security Invariants

- Dockerfile frontend and base image remain digest-pinned.
- Python dependencies remain version- and wheel-hash-locked.
- Docker build context remains allowlisted.
- The OCI archive is never extracted during verification.
- Archive paths, member types, descriptor sizes, descriptor digests, platform,
  user, working directory, entrypoint, command override, and rootfs diff IDs
  fail closed on drift.
- Release actions remain pinned to reviewed commit SHAs.
- Buildx and BuildKit versions are fixed; the BuildKit container image is
  digest-pinned, CDI is disabled, and insecure BuildKit entitlements are not
  enabled.
- Attestation uses GitHub OIDC; no long-lived signing secret is introduced.
- The archive, source, generated layers, host paths, and command lines are not
  serialized into public TUC evidence.

## Claim Boundary

The repository can prove that its release workflow is configured to emit and
attest a verified OCI archive. Until a release run exists and its attestation
is independently verified, TUC does not claim published image provenance,
byte-identical reproducible images, a public registry image, production source
ingestion, or a production sandbox.

Independent security review remains a separate admission requirement.

## Public Evidence Promotion

The OCI ingestion proof and release-provenance readiness report are admitted to
the separate Objective Alpha Public Evidence Catalog, not the fixed sixteen
entry Public Proof Bundle. Their catalog contracts are implemented by:

- `examples/objective_alpha_public_evidence_catalog.py`
- `schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json`
- `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md`

The new extension tiers are `isolation_proof` and
`supply_chain_readiness`. Objective Beta binds both reports directly and keeps
external attestation verification, public registry publication, production
source ingestion, and production sandbox claims blocked.
