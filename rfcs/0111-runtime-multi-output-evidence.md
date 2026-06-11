# RFC 0111: Runtime Multi-Output Evidence Fixture v0

- Status: Accepted
- Date: 2026-06-11
- Related:
  - [Runtime Output Manifest](../docs/RUNTIME_OUTPUT_MANIFEST.md)
  - [Runtime Reference Correctness](../docs/RUNTIME_REFERENCE_CORRECTNESS.md)
  - [Runtime Executor v0](../docs/RUNTIME_EXECUTOR.md)
  - `examples/runtime_multi_output_evidence.py`
  - `tests/golden/runtime_multi_output_evidence/current_report.json`

## Summary

Add a deterministic multi-output runtime evidence fixture proving that Runtime
Output Manifest and Runtime Reference Correctness work on a branched graph with
two terminal outputs.

## Motivation

The first runtime output and correctness evidence used `proof_of_execution`,
which has one terminal output. That is enough to prove the boundary exists, but
not enough to catch ordering, producer provenance, or reference-inventory
mistakes once graphs branch and return more than one result.

TUC needs a small practical fixture that keeps the evidence path honest before
runtime APIs, allocation planning, or executable backend work become richer.

## Decision

The fixture builds a fixed graph:

```text
matmul -> projection -> reduction -> row_sum
                    -> relu      -> positive_projection
```

The example:

- compiles the graph with the linear algebra simulator capability
- executes it through Runtime Executor v0
- derives terminal outputs from graph structure
- builds Runtime Output Manifest evidence for both terminal outputs
- builds Runtime Reference Correctness evidence for both terminal outputs
- serializes only metadata and omission policies
- stores one deterministic combined golden report

The fixture does not introduce a new executor API, new backend trust boundary,
or new runtime operation kind.

## Non-Goals

- multi-output operation kernels
- user-defined API return aliases
- tensor-value serialization
- tensor-content hashing
- native backend correctness claims
- native performance claims
- external executable backend approval
- plugin discovery or artifact loading

## Security Boundary

The fixture is metadata-only. It must not serialize output tensors, reference
tensors, tensor hashes, host paths, device identifiers, generated code, command
lines, environment variables, plugin entrypoints, network locations, benchmark
samples, JIT artifacts, or native executable artifacts.

The example uses only trusted in-process Runtime Executor v0 behavior and the
existing simulator backend capability.

## Acceptance Criteria

- A runnable example emits deterministic combined multi-output evidence.
- Golden evidence records exactly two terminal outputs.
- Runtime Output Manifest preserves output producer metadata for both outputs.
- Runtime Reference Correctness compares both outputs against independent
  references.
- Tests assert the fixture omits raw tensor values.
- Existing output-manifest and reference-correctness evidence remains unchanged.
