# Objective Beta Reproducibility Capsule

Objective Beta Reproducibility Capsule v0 turns the current research claim
into a compact, reviewer-facing digest manifest. It advances Objective Beta
from a project-owned claim snapshot to repository-local reproducibility:
another reviewer can verify the exact evidence closure without executing
source, the compiler pipeline, the runtime, a backend, or a generated artifact.

## Research Question

Can the Objective Beta claim, its gate, and every direct supporting artifact
be identified and integrity-checked from versioned data alone?

The current answer is `reproducible_from_repository_goldens` for this bounded
evidence set.

## Capsule Contents

The capsule binds eleven JSON artifacts by SHA-256 digest:

1. Objective Alpha Research Claim Gate
2. Source-To-Intent Research Kernel Ingress Proof Bundle
3. First Real Triton Kernel Path
4. Real Triton First Slice Evidence Portfolio
5. Real Triton First Slice Admission Readiness Gate
6. Real Triton First Slice Maintainer Approval Request
7. Research Scope Claim Gate
8. OCI Source Ingestion Research Proof
9. OCI Source Worker Release Provenance Readiness
10. Objective Beta Research Claim
11. Objective Beta Research Claim Gate

The serialized capsule carries artifact IDs, roles, content types, digests, and
claim-boundary flags. It does not carry repository paths, source text, Source
Intent payloads, tensor values, runtime handles, device identifiers, generated
code, backend artifacts, commands, or benchmark samples.

## Trust Boundary

Artifact locations exist only in a fixed in-repository allowlist in
`examples/objective_beta_reproducibility_capsule.py`. They are not accepted
from the capsule. Absolute paths and parent traversal are rejected before any
artifact read. Every artifact must be valid source-free JSON.

The capsule verifies that:

- the Beta claim and claim gate satisfy their v0 contracts;
- the claim gate binds the exact serialized claim digest;
- all nine claim evidence entries bind the exact allowlisted artifact bytes;
- evidence order and roles match the frozen v0 contract;
- source ingestion, native performance, and vendor replacement remain blocked;
- external maintainer approval remains required.

## Run

```bash
python examples/objective_beta_reproducibility_capsule.py
```

The independent replay command is documented in
[Objective Beta Reproducibility Gate](OBJECTIVE_BETA_REPRODUCIBILITY_GATE.md).
The shortest external reproduction path is
[Reproducing Objective Beta](REPRODUCING_OBJECTIVE_BETA.md).

## Artifacts

- Schema: `schemas/objective_beta_reproducibility_capsule_report.v0.schema.json`
- Entrypoint: `examples/objective_beta_reproducibility_capsule.py`
- Golden: `tests/golden/proofs/objective_beta_reproducibility_capsule.json`
- Gate: `examples/objective_beta_reproducibility_gate.py`
- RFC: `rfcs/0281-objective-beta-reproducibility-capsule.md`

## Non-Claims

The capsule is evidence integrity and reproducibility metadata. It does not
admit source ingestion, prove native execution, prove performance parity,
approve a frontend, or turn TUC into a production compiler.
