# RFC 0290: OCI Source Worker Release Provenance

Status: Accepted for research release artifacts

## Decision

TUC will build the source-ingestion worker as an OCI Image Layout archive in
the protected release workflow. Before attestation, repository-owned code must
validate the archive descriptor graph and the fixed runtime configuration. The
workflow then generates a worker-specific CycloneDX SBOM, writes checksums,
and uses GitHub OIDC artifact attestations for both provenance and SBOM.
After attestation, the same GitHub-hosted run must verify worker provenance
through GitHub CLI policy enforcement and emit a bounded metadata-only receipt.

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
- Verification binds repository, signer workflow, source commit, source ref,
  OIDC issuer, SLSA provenance predicate, and GitHub-hosted runner policy.
- The verification receipt is generated only after the verifier exits zero,
  is included in the checksum manifest, and remains non-authorizing.
- The archive, source, generated layers, host paths, and command lines are not
  serialized into public TUC evidence.
- Raw verifier output and attestation bundles are not uploaded in the release
  artifact bundle.
- A release-tag trigger is not treated as evidence that external repository
  ruleset protection was verified.
- The runner-provided GitHub CLI version is recorded; pinning that tool remains
  release-hardening work.

## Claim Boundary

The repository can prove that its release workflow is configured to emit,
attest, and same-run verify an OCI archive. Until a release run exists, this is
configuration readiness rather than executed release evidence. Same-run
verification is also not independent consumer verification. TUC does not claim
published image provenance, byte-identical reproducible images, a public
registry image, production source ingestion, or a production sandbox.

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
