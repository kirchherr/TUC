# RFC 0270: Evidence Graph Acyclicity Gate

## Status

Accepted as source-ingestion evidence-graph safety evidence.

## Context

The Real Triton First Slice Plan, Source Ingestion Maintainer Security Review
Packet, Maintainer Approval Artifact, Source Ingestion Admission Gate, and
Research Scope Claim Gate now form a digest-bound evidence chain.

That chain must stay acyclic. Downstream review artifacts may bind upstream
planning artifacts, but upstream planning artifacts must not bind downstream
review or admission artifacts back into themselves.

## Decision

Add `evidence_graph_acyclicity_gate` as a data-only, source-free report that
builds the current source-ingestion evidence graph and rejects cycles.

The graph uses the edge direction:

```text
dependent_report -> bound_evidence
```

The initial gate covers 18 nodes and 27 digest-binding edges. It records:

- `cycle_count = 0`;
- empty `detected_cycles`;
- dependency-first topological order;
- source-free nodes;
- digest-only edges.

## Non-Goals

This RFC does not authorize source ingestion, source-to-ComputeGraph lowering,
source-to-HAC-IR lowering, source-to-runtime-plan lowering, package import,
plugin discovery, Triton JIT, device access, generated artifact execution,
native backend execution, or performance claims.

It also does not introduce a general source parser or execute any evidence
artifact. The graph is assembled from existing data-only reports.

## Artifacts

- Module: `src/tuc/evidence_graph_acyclicity.py`
- Example: `examples/evidence_graph_acyclicity_gate.py`
- Schema: `schemas/evidence_graph_acyclicity_gate_report.v0.schema.json`
- Golden: `tests/golden/frontend/evidence_graph_acyclicity_gate_report.json`
- Tests: `tests/test_evidence_graph_acyclicity_gate.py`
- Doc: `docs/EVIDENCE_GRAPH_ACYCLICITY_GATE.md`

## Consequences

The source-ingestion evidence chain now has a machine-checkable DAG invariant.
Future changes that create a circular digest dependency fail before they can
support source-ingestion readiness or research-scope claims.
