# RFC 0125: Runtime Evidence Matrix Input Manifest Coverage

## Status

Accepted.

## Context

Runtime Evidence Gate now requires Runtime Input Manifest v0. If the curated
Runtime Evidence Matrix does not also require `input_manifest`, the gate and
the proof inventory can drift: a graph can appear complete in the matrix while
the merge gate requires additional runtime input evidence outside that matrix.

## Decision

Add `input_manifest` as a required Runtime Evidence Matrix artifact kind.

The matrix now:

- includes `input_manifest` in supported artifact kinds
- includes `input_manifest` in required artifact kinds
- lists one `input_manifest` artifact identifier for every accepted graph
  fixture
- keeps artifact identifiers as bounded data-only IDs, not file paths
- keeps the Matrix execution-free and repository-scan-free

Related schema and golden:

```text
schemas/runtime_evidence_matrix_report.v0.schema.json
tests/golden/proofs/runtime_evidence_matrix_report.json
```

Runtime Input Manifest schema:

```text
schemas/runtime_input_manifest_report.v0.schema.json
```

## Security Boundary

This change adds only curated metadata identifiers to the matrix. It does not
load artifact files, inspect host paths, scan the repository, execute generated
artifacts, import plugins, load dynamic libraries, touch devices, run JIT code,
spawn subprocesses, or access the network.

## Acceptance Criteria

- `input_manifest` appears in `RUNTIME_EVIDENCE_ARTIFACT_KINDS`.
- `input_manifest` appears in `RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KINDS`.
- Every current graph fixture remains runtime-evidence complete.
- Runtime Evidence Gate requires and reports Runtime Input Manifest.
- The runtime evidence matrix schema and golden include `input_manifest`.
