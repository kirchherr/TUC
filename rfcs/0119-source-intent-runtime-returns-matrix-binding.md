# RFC 0119: Source Intent Runtime Returns Matrix Binding

- Status: Accepted
- Related:
  - [Source Intent Runtime Returns](../docs/SOURCE_INTENT_RUNTIME_RETURNS.md)
  - [Runtime Evidence Matrix](../docs/RUNTIME_EVIDENCE_MATRIX.md)
  - [Runtime Evidence Gate](../docs/RUNTIME_EVIDENCE_GATE.md)
  - [RFC 0118](0118-source-intent-runtime-returns-gate-coverage.md)

## Summary

Bind Source Intent Runtime Returns gate evidence to the curated Runtime Evidence
Matrix graph that inventories the same frontend-originated fixture.

## Motivation

RFC 0118 made Source Intent Runtime Returns part of the Runtime Evidence Gate.
That proves the standalone report is valid, but the gate should also fail if
the curated matrix forgets the frontend return fixture while a separate report
continues to pass.

The matrix binding turns the frontend return proof into a single reviewable
evidence chain:

- Source Intent return semantics exist before execution.
- Runtime evidence exists for the same accepted graph fixture.
- Source Intent Runtime Returns resolves that fixture through Runtime Output
  Contract and Runtime Public Output Bundle after trusted prototype execution.

## Design

Runtime Evidence Gate requires:

- graph ID `source_intent_return_mlp` is present in Runtime Evidence Matrix
- source boundary is `source_intent_metadata`
- graph is runtime-evidence complete
- artifact kinds `source_intent_return_semantics` and
  `source_intent_runtime_returns` are present
- Source Intent Runtime Returns report `module_name` and `graph_name` both match
  the matrix graph ID

The gate report now emits:

```text
source_intent_runtime_returns_matrix = "covered"
```

## Non-Goals

- requiring Source Intent return artifacts for non-Source-Intent graphs
- changing Source Intent Runtime Returns schema
- changing runtime execution semantics
- enabling source parsing or executable backend discovery

## Security

The binding is data-only. It checks bounded graph IDs, source-boundary labels,
artifact-kind labels, completeness metadata, and report graph names. It does
not scan paths, import plugins, execute generated artifacts, load raw tensor
values, access devices, call the network, or spawn subprocesses.

## Acceptance Criteria

- Runtime Evidence Gate rejects a matrix without `source_intent_return_mlp`.
- Runtime Evidence Gate rejects a Source Intent matrix graph missing
  `source_intent_runtime_returns`.
- Runtime Evidence Gate rejects a Source Intent Runtime Returns report for a
  different graph name.
- Runtime Evidence Gate golden includes
  `source_intent_runtime_returns_matrix = "covered"`.
- Full test suite remains green.
