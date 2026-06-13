# RFC 0141: Runtime Evidence Matrix Scoped Requirements

## Status

Accepted.

## Context

Runtime Evidence Matrix v0 originally used one global required evidence list for
every graph fixture. That worked while all accepted graph entries represented
full runtime proof flows with HAC-IR, runtime plan, readiness, trace, manifests,
reference correctness, and execution receipt evidence.

Backend Equivalence fixtures are different. They are data-only reports that
compare trusted runtime placements of the same graph. Treating them as ordinary
full proof fixtures would either make the matrix permanently incomplete or
encourage fake placeholder evidence identifiers.

## Decision

Runtime Evidence Matrix graph entries now declare `required_artifact_kinds`.

Standard runtime proof graphs continue to require the full default set:

- `hac_ir_golden`
- `runtime_plan_golden`
- `compiler_decision_golden`
- `execution_readiness_golden`
- `execution_trace_golden`
- `tensor_store_evidence`
- `input_manifest`
- `output_contract`
- `public_output_bundle`
- `reference_correctness`
- `execution_receipt`

Backend Equivalence graph entries use a scoped required set:

- `backend_equivalence`

The current matrix now inventories:

- `runtime_backend_equivalence`
- `runtime_vector_backend_equivalence`
- `runtime_mixed_backend_equivalence`

Each uses source boundary `runtime_backend_equivalence`, graph family
`backend_equivalence`, and the scoped `backend_equivalence` requirement.

## Security Boundary

Scoped requirements are bounded data only. They do not scan files, resolve
paths, import code, discover backends, execute examples, load artifacts, access
devices, run subprocesses, or authorize native execution.

Artifact kinds and source boundaries remain closed enums. Unknown kinds,
duplicate required kinds, duplicate graph IDs, path-like identifiers, and known
execution-surface identifiers fail closed.

## Consequences

The Runtime Evidence Matrix can now inventory different evidence families
without weakening completeness semantics.

Backend Equivalence fixtures become visible in the same CI-facing proof
inventory as runtime proofs, while still preserving their narrower data-only
review meaning.
