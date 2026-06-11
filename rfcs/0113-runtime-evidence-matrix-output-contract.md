# RFC 0113: Runtime Evidence Matrix Output Contract Coverage

- Status: Accepted
- Date: 2026-06-11
- Related:
  - [Runtime Evidence Matrix](../docs/RUNTIME_EVIDENCE_MATRIX.md)
  - [Runtime Evidence Gate](../docs/RUNTIME_EVIDENCE_GATE.md)
  - [Runtime Output Contract](../docs/RUNTIME_OUTPUT_CONTRACT.md)
  - `schemas/runtime_evidence_matrix_report.v0.schema.json`
  - `tests/golden/proofs/runtime_evidence_matrix_report.json`

## Summary

Add `output_contract` as a required Runtime Evidence Matrix artifact kind so
the curated proof inventory matches the Runtime Evidence Gate requirement for
public output alias evidence.

## Motivation

Runtime Evidence Gate now requires Runtime Output Contract evidence. If the
Matrix does not also list that evidence kind, the repository has two slightly
different definitions of runtime completeness: one in the gate, one in the
inventory.

TUC needs those definitions to stay aligned because the Matrix is the
review-facing map of accepted runtime proof evidence.

## Decision

Runtime Evidence Matrix now:

- includes `output_contract` in supported artifact kinds
- includes `output_contract` in required artifact kinds
- lists one `output_contract` artifact identifier for every current accepted
  graph fixture
- keeps artifact identifiers as bounded data-only IDs, not file paths
- keeps the Matrix execution-free and repository-scan-free

## Non-Goals

- loading artifact files from the Matrix
- verifying filesystem paths
- serializing tensor values
- introducing positional return semantics
- changing Runtime Executor behavior
- changing Runtime Output Contract schema

## Security Boundary

This change adds only curated metadata identifiers. It does not scan the
repository, execute examples, import plugins, load generated artifacts, touch
devices, run JIT code, spawn subprocesses, or access the network.

Artifact IDs remain bounded safe identifiers and continue to reject known
execution-surface names and path-like strings.

## Acceptance Criteria

- `output_contract` appears in `RUNTIME_EVIDENCE_ARTIFACT_KINDS`.
- `output_contract` appears in `RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KINDS`.
- Every current graph fixture remains runtime-evidence complete.
- The runtime evidence matrix schema and golden include `output_contract`.
- Runtime Evidence Gate still passes.
