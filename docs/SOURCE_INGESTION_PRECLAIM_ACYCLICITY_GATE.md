# Source Ingestion Pre-Claim Acyclicity Gate

Source Ingestion Pre-Claim Acyclicity Gate v0 is the data-only CI gate that
proves the source-ingestion evidence chain is acyclic before the project-level
Research Scope Claim Gate binds it.

Run it with:

```bash
python examples/source_ingestion_preclaim_acyclicity_gate.py
```

## What It Checks

The gate models evidence binding edges as:

```text
dependent_report -> bound_evidence
```

The pre-claim graph covers:

- Real Triton First Slice Plan and its prerequisite evidence.
- Source Ingestion Maintainer Security Review Packet.
- Source Ingestion Maintainer Approval Artifact.
- Source Ingestion Admission Gate.

It deliberately excludes `research_scope_claim_gate`. That lets Research Scope
bind the acyclicity result by digest without creating a report that depends on
itself.

The report currently emits:

```text
node_count = 17
edge_count = 25
cycle_count = 0
gate_status = PASS
```

## Why It Exists

The global Evidence Graph Acyclicity Gate can show the whole current
source-ingestion graph, including Research Scope. But Research Scope also needs
a safe upstream acyclicity artifact to bind.

This gate is that upstream artifact: it proves the source-ingestion chain is a
DAG through Admission, and it forbids Research Scope from appearing inside that
pre-claim graph.

## Security Boundary

The report is source-free and edge-digest-only. It does not serialize source
text, Source Intent payloads, tensor values, runtime handles, host paths,
commands, device identifiers, plugin entrypoints, generated code, backend
artifacts, executable artifacts, or native benchmark output.

It does not parse source, import external packages, discover plugins, run
Triton JIT, access devices, load dynamic libraries, spawn subprocesses, touch
the network, emit generated artifacts, or authorize source-to-HAC-IR or
source-to-runtime-plan shortcuts.

## Contract

- Example: `examples/source_ingestion_preclaim_acyclicity_gate.py`
- Schema: `schemas/source_ingestion_preclaim_acyclicity_gate_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_ingestion_preclaim_acyclicity_gate_report.json`
- Tests: `tests/test_source_ingestion_preclaim_acyclicity_gate.py`
- Shared module: `src/tuc/evidence_graph_acyclicity.py`
- RFC: `rfcs/0271-source-ingestion-preclaim-acyclicity-gate.md`
- Global Acyclicity Gate: [Evidence Graph Acyclicity Gate](EVIDENCE_GRAPH_ACYCLICITY_GATE.md)
- Research Scope Claim Gate: [Research Scope Claim Gate](RESEARCH_SCOPE_CLAIM_GATE.md)
