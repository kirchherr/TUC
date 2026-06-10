# RFC 0087: Runtime Evidence Matrix

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha

## Summary

Add a deterministic Runtime Evidence Matrix report that inventories proof and
runtime evidence coverage across accepted graph fixtures.

## Motivation

TUC now has multiple proof graphs, frontend-originated metadata examples,
runtime plans, compiler decision reports, readiness reports, execution traces,
and correctness references. Without one matrix, reviewers must reconstruct the
state by hand.

The matrix makes the proof ladder inspectable without adding a parser,
filesystem scanner, backend discovery mechanism, or executable backend path.

## Decision

Add:

- `RuntimeEvidenceArtifact`
- `RuntimeEvidenceGraph`
- `RuntimeEvidenceMatrixReport`
- `build_runtime_evidence_matrix_report`
- `dump_runtime_evidence_matrix_report`
- `schemas/runtime_evidence_matrix_report.v0.schema.json`
- `examples/runtime_evidence_matrix.py`
- `tests/golden/proofs/runtime_evidence_matrix_report.json`

The report is complete only when every graph has:

- HAC-IR golden evidence
- runtime-plan golden evidence
- compiler-decision golden evidence
- execution-readiness golden evidence
- execution-trace golden evidence
- independent reference-correctness evidence

## Security Model

The report accepts bounded identifiers only. It rejects path-like artifact IDs,
known execution-surface identifiers, unsupported artifact kinds, unsupported
source boundaries, duplicate graph IDs, duplicate artifact kinds, and issue
lists that do not match the derived missing-evidence set.

It does not execute code, import modules, inspect host paths, read artifacts,
load backend binaries, discover plugins, access devices, spawn subprocesses,
open the network, run JIT code, or approve generated artifact execution.

## Consequences

- Reviewers can see which graph fixtures are fully evidenced and which still
  need runtime proof work.
- The Triton-like MVP metadata path is visible as the first fully runtime-
  evidenced row.
- Future proof-graph work can target specific missing evidence cells instead of
  adding broad architecture.

## References

- [Runtime Evidence Matrix](../docs/RUNTIME_EVIDENCE_MATRIX.md)
- [Runtime Executor v0](../docs/RUNTIME_EXECUTOR.md)
- `schemas/runtime_evidence_matrix_report.v0.schema.json`
- `examples/runtime_evidence_matrix.py`
- `tests/golden/proofs/runtime_evidence_matrix_report.json`
