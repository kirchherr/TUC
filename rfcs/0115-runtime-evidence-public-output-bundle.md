# RFC 0115: Runtime Evidence Public Output Bundle Coverage

- Status: Accepted
- Date: 2026-06-11
- Related:
  - [Runtime Evidence Matrix](../docs/RUNTIME_EVIDENCE_MATRIX.md)
  - [Runtime Evidence Gate](../docs/RUNTIME_EVIDENCE_GATE.md)
  - [Runtime Public Output Bundle](../docs/RUNTIME_PUBLIC_OUTPUT_BUNDLE.md)
  - [Runtime Output Contract](../docs/RUNTIME_OUTPUT_CONTRACT.md)
  - `schemas/runtime_evidence_matrix_report.v0.schema.json`
  - `schemas/runtime_public_output_bundle_report.v0.schema.json`
  - `tests/golden/proofs/runtime_evidence_matrix_report.json`
  - `tests/golden/proofs/runtime_evidence_gate.txt`

## Summary

Add `public_output_bundle` as a required Runtime Evidence Matrix artifact kind
and require Runtime Evidence Gate to verify Runtime Public Output Bundle v0.

## Motivation

Runtime Output Contract proves that public output names bind to terminal graph
tensor names. Runtime Public Output Bundle proves the next practical boundary:
those public names resolve to read-only runtime values while review evidence
stays metadata-only.

If the bundle is optional, TUC can claim public output semantics without proving
the runtime return surface. That would leave a gap between abstract output names
and actual executable prototype behavior.

## Decision

Runtime Evidence Matrix now:

- includes `public_output_bundle` in supported artifact kinds
- includes `public_output_bundle` in required artifact kinds
- lists one `public_output_bundle` artifact identifier for every current
  accepted graph fixture
- keeps artifact identifiers as bounded data-only IDs, not file paths
- keeps the Matrix execution-free and repository-scan-free

Runtime Evidence Gate now:

- builds Runtime Public Output Bundle evidence
- requires bundle graph name, output contract, public names, tensor names, and
  raw-value policy to match Runtime Output Contract evidence
- requires bundle values to be read-only
- reports Runtime Public Output Bundle status in the deterministic gate output

## Non-Goals

- serializing tensor values into Matrix or Gate evidence
- tensor-content hashing
- positional tuple return semantics
- loading artifact files from Matrix identifiers
- changing Runtime Executor execution behavior
- authorizing external executable backends

## Security Boundary

This change adds only curated metadata identifiers to the Matrix and a bounded
in-memory bundle check to the Gate. It does not scan the repository, execute
generated artifacts, import plugins, load dynamic libraries, touch devices, run
JIT code, spawn subprocesses, or access the network.

Runtime Public Output Bundle may hold in-memory values, but the schema-versioned
report and gate output omit raw tensor values by policy.

## Acceptance Criteria

- `public_output_bundle` appears in `RUNTIME_EVIDENCE_ARTIFACT_KINDS`.
- `public_output_bundle` appears in `RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KINDS`.
- Every current graph fixture remains runtime-evidence complete.
- Runtime Evidence Gate requires and reports Runtime Public Output Bundle.
- Runtime Evidence Gate rejects a bundle that does not match Runtime Output
  Contract evidence.
- The runtime evidence matrix schema, matrix golden, and gate golden include the
  new coverage.
