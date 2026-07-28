# RFC 0281: Objective Beta Reproducibility Capsule

Status: Accepted

## Summary

Introduce a digest-only Objective Beta Reproducibility Capsule and an offline
Replay Gate. Together they let an external reviewer integrity-check the Beta
claim closure from fixed repository JSON artifacts without executing source,
compiler passes, runtime code, backends, plugins, devices, subprocesses,
network operations, or generated artifacts.

## Motivation

Objective Beta already binds the strongest current research evidence, but a
claim assembled by project code is not yet the strongest reproducibility
story. Proof Ladder Level 3 requires another reviewer to verify exactly which
artifacts support the claim and whether any byte, order, or boundary changed.

The capsule is intentionally smaller than a release archive. It is a manifest
of source-free evidence identities, roles, and SHA-256 digests. The gate is an
independent replay of those links from a static internal allowlist.

## Decision

Add:

- `examples/objective_beta_reproducibility_capsule.py`
- `examples/objective_beta_reproducibility_gate.py`
- `schemas/objective_beta_reproducibility_capsule_report.v0.schema.json`
- `schemas/objective_beta_reproducibility_gate_report.v0.schema.json`
- `tests/golden/proofs/objective_beta_reproducibility_capsule.json`
- `tests/golden/proofs/objective_beta_reproducibility_gate.json`
- `docs/OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE.md`
- `docs/OBJECTIVE_BETA_REPRODUCIBILITY_GATE.md`
- `docs/REPRODUCING_OBJECTIVE_BETA.md`

The capsule binds the seven direct Beta dependencies, the Beta claim, and its
gate. It exposes no repository paths. Artifact locations remain a fixed code
allowlist and reject absolute paths or parent traversal.

## Security Invariants

- Inputs are parsed as JSON data, never behavior.
- The capsule cannot select file locations.
- The allowlist must match the frozen artifact ID set exactly.
- All reports reject additional properties and unexpected ordering.
- Source and runtime-sensitive fields remain forbidden.
- Replay performs no imports from external packages, no subprocesses, no
  network access, no device access, and no generated-artifact execution.
- Source ingestion and product, performance, hardware, and vendor-replacement
  claims remain blocked.
- External maintainer approval remains required and is not synthesized.

## CI

The standard read-only CI `pytest -q` job runs capsule and replay contract,
golden, example, artifact-tampering, allowlist-drift, source-leakage,
evidence-reordering, schema-closure, and blocked-claim tests. No separate
workflow step is added because `ci.yml` is itself digest-bound evidence.

## Alternatives Rejected

### Archive all evidence payloads inside one report

Rejected because it duplicates large artifacts and increases accidental data
disclosure risk.

### Re-execute the entire compiler and runtime during replay

Rejected for this gate because it would mix artifact integrity with executable
trust and make external review depend on a larger attack surface. Existing
proof tests continue to cover execution separately.

### Accept artifact paths from the capsule

Rejected because untrusted paths would create traversal and confused-deputy
risks. The replay verifier owns the fixed mapping.

## Consequences

Objective Beta becomes independently replayable at the artifact-integrity
layer. Any evidence mutation requires an explicit capsule and golden update,
making research-claim drift visible in review. This does not widen source or
backend execution surfaces.
