# Evidence Graph Acyclicity Gate

Evidence Graph Acyclicity Gate v0 is the data-only CI gate that proves the
current source-ingestion evidence chain is a directed acyclic graph.

Run it with:

```bash
python examples/evidence_graph_acyclicity_gate.py
```

## What It Checks

The gate models evidence binding edges as:

```text
dependent_report -> bound_evidence
```

The current graph covers:

- Real Triton First Slice Plan and its prerequisite evidence.
- Source Ingestion Maintainer Security Review Packet.
- Source Ingestion Maintainer Approval Artifact.
- Source Ingestion Admission Gate.
- Research Scope Claim Gate source-ingestion bindings.

The report currently emits:

```text
node_count = 18
edge_count = 27
cycle_count = 0
gate_status = PASS
```

## Why It Exists

TUC intentionally allows downstream review artifacts to bind upstream planning
artifacts by digest. It must not allow an upstream planning artifact to bind a
downstream review or admission artifact back into itself.

This gate makes that rule machine-reviewable. If a future edit accidentally
creates a path such as:

```text
first_slice_plan -> maintainer_review_packet -> first_slice_plan
```

the gate fails closed before the source-ingestion boundary can be claimed as
review-ready.

## Security Boundary

The report is source-free and edge-digest-only. It does not serialize source
text, Source Intent payloads, tensor values, runtime handles, host paths,
commands, device identifiers, plugin entrypoints, generated code, backend
artifacts, executable artifacts, or native benchmark output.

It does not import external packages, discover plugins, run Triton JIT, access
devices, load dynamic libraries, spawn subprocesses, touch the network, emit
generated artifacts, or authorize source-to-HAC-IR or source-to-runtime-plan
shortcuts.

## Contract

- Module: `src/tuc/evidence_graph_acyclicity.py`
- Example: `examples/evidence_graph_acyclicity_gate.py`
- Schema: `schemas/evidence_graph_acyclicity_gate_report.v0.schema.json`
- Golden: `tests/golden/frontend/evidence_graph_acyclicity_gate_report.json`
- Tests: `tests/test_evidence_graph_acyclicity_gate.py`
- RFC: `rfcs/0270-evidence-graph-acyclicity-gate.md`
- Real Triton First Slice Plan: [Real Triton First Slice Plan](REAL_TRITON_FIRST_SLICE_PLAN.md)
- Maintainer Review Packet: [Source Ingestion Maintainer Security Review Packet](SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md)
- Maintainer Approval Artifact: [Source Ingestion Maintainer Approval Artifact](SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT.md)
- Source Ingestion Admission Gate: [Source Ingestion Admission Gate](SOURCE_INGESTION_ADMISSION_GATE.md)
- Research Scope Claim Gate: [Research Scope Claim Gate](RESEARCH_SCOPE_CLAIM_GATE.md)
