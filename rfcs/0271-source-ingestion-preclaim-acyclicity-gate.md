# RFC 0271: Source Ingestion Pre-Claim Acyclicity Gate

## Status

Accepted for Objective Alpha source-ingestion evidence hardening.

## Context

The Evidence Graph Acyclicity Gate proves that the current source-ingestion
digest graph is acyclic through Research Scope. However, Research Scope cannot
directly bind that full graph as one of its own required evidence items without
creating a self-referential claim surface.

TUC needs an upstream acyclicity artifact that ends before Research Scope.

## Decision

Add Source Ingestion Pre-Claim Acyclicity Gate v0.

The gate covers:

- Real Triton First Slice Plan.
- Source Ingestion Maintainer Security Review Packet.
- Source Ingestion Maintainer Approval Artifact.
- Source Ingestion Admission Gate.

The gate excludes:

- Research Scope Claim Gate.
- Source text, Source Intent payload bodies, tensor values, runtime handles,
  device identifiers, host paths, commands, generated code, backend artifacts,
  plugin entrypoints, native benchmark output, and executable artifacts.

The gate emits a source-free, digest-only DAG report with:

- `node_count = 17`
- `edge_count = 25`
- `cycle_count = 0`
- `gate_status = PASS`

## Security Requirements

- No source parsing.
- No Python module or package import from user-controlled paths.
- No plugin discovery.
- No JIT.
- No device access.
- No subprocess execution.
- No generated artifact execution.
- No native backend execution.
- No filesystem or network expansion.
- Fail closed on missing nodes, missing edge endpoints, duplicate nodes,
  duplicate edges, cycle detection, scope leakage, malformed digests, and
  source-like forbidden fragments.

## Review Impact

Research Scope may bind this pre-claim gate by digest because the gate excludes
Research Scope from its own graph. The global Evidence Graph Acyclicity Gate
may still include Research Scope as the downstream claim view.

## Implementation

- Example: `examples/source_ingestion_preclaim_acyclicity_gate.py`
- Schema: `schemas/source_ingestion_preclaim_acyclicity_gate_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_ingestion_preclaim_acyclicity_gate_report.json`
- Tests: `tests/test_source_ingestion_preclaim_acyclicity_gate.py`
- Documentation: `docs/SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE.md`
