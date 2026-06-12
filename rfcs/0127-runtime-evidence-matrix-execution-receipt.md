# RFC 0127: Runtime Evidence Matrix Execution Receipt Coverage

## Status

Accepted.

## Context

Runtime Evidence Gate now requires Runtime Execution Receipt v0. If the Runtime
Evidence Matrix does not also require `execution_receipt`, a graph can appear
complete in the curated proof inventory while missing the final linked runtime
execution evidence that the gate expects.

## Decision

Add `execution_receipt` as a required Runtime Evidence Matrix artifact kind.

The matrix now:

- includes `execution_receipt` in supported artifact kinds
- includes `execution_receipt` in required artifact kinds
- lists one `execution_receipt` artifact identifier for every accepted graph
  fixture
- keeps artifact identifiers as bounded data-only IDs, not file paths
- keeps the Matrix execution-free and repository-scan-free

Related schema and golden:

```text
schemas/runtime_evidence_matrix_report.v0.schema.json
tests/golden/proofs/runtime_evidence_matrix_report.json
```

Runtime Execution Receipt schema:

```text
schemas/runtime_execution_receipt_report.v0.schema.json
```

## Security Boundary

This change adds only curated metadata identifiers to the matrix. It does not
load receipt files, inspect host paths, scan the repository, execute generated
artifacts, import plugins, load dynamic libraries, touch devices, run JIT code,
spawn subprocesses, or access the network.

## Acceptance Criteria

- `execution_receipt` appears in `RUNTIME_EVIDENCE_ARTIFACT_KINDS`.
- `execution_receipt` appears in `RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KINDS`.
- Every current graph fixture remains runtime-evidence complete.
- Runtime Evidence Gate requires and reports Runtime Execution Receipt.
- The runtime evidence matrix schema and golden include `execution_receipt`.
