# Source Ingestion Admission Gate

Source Ingestion Admission Gate v0 is the fail-closed admission gate for the
first possible `direct_source_ingestion` slice.

It does not approve or admit source ingestion. The current report keeps:

```text
admitted = false
approval_artifact_present = false
source_ingestion_admission_ready = false
```

Run it with:

```bash
python examples/source_ingestion_admission_gate.py
```

## What It Binds

The gate binds the Source Ingestion Maintainer Security Review Packet by
SHA-256 metadata digest. The review packet in turn binds the admitted-slice
RFC, bounded source buffer, sandbox, parser fuzz negative corpus, source-free
diagnostics, Source-To-Intent plain-data golden, CI replay, and first-slice
plan evidence.

## Meaning

This gate turns the source-ingestion boundary into an explicit machine-checkable
decision point:

- review evidence is present;
- external maintainer approval is still absent;
- direct source ingestion remains denied;
- source-to-ComputeGraph, source-to-HAC-IR, and source-to-runtime-plan paths
  remain denied.

Before `direct_source_ingestion` can become admitting, TUC still requires:

- maintainer security review approval.

## Security Boundary

The report is digest-only and source-free. It does not serialize source text,
Source Intent payloads, tensor values, runtime handles, host paths, command
lines, device identifiers, plugin entrypoints, generated code, backend
artifacts, native benchmark output, or executable artifacts.

It does not import external packages, discover plugins, run Triton JIT, access
devices, load dynamic libraries, spawn subprocesses, touch the network, emit
generated artifacts, or authorize source-to-ComputeGraph, source-to-HAC-IR, or
source-to-runtime-plan shortcuts.

## Contract

- Module: `src/tuc/frontend/source_ingestion_admission_gate.py`
- Example: `examples/source_ingestion_admission_gate.py`
- Schema: `schemas/source_ingestion_admission_gate_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_ingestion_admission_gate_report.json`
- Tests: `tests/test_source_ingestion_admission_gate.py`
- RFC: `rfcs/0266-source-ingestion-admission-gate.md`
- Review Packet: [Source Ingestion Maintainer Security Review Packet](SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md)
- Source Ingestion Approval Criteria: [Source Ingestion Approval Criteria](SOURCE_INGESTION_APPROVAL_CRITERIA.md)
- Source Ingestion Approval Criteria Doc: `docs/SOURCE_INGESTION_APPROVAL_CRITERIA.md`
- Source Ingestion Approval Criteria Module: `src/tuc/frontend/source_ingestion_approval_criteria.py`
- Source Ingestion Approval Criteria Example: `examples/source_ingestion_approval_criteria.py`
- Source Ingestion Approval Criteria Schema: `schemas/source_ingestion_approval_criteria_report.v0.schema.json`
- Source Ingestion Approval Criteria Golden: `tests/golden/frontend/source_ingestion_approval_criteria_report.json`
- Source Ingestion Approval Criteria RFC: `rfcs/0268-source-ingestion-approval-criteria.md`
- Maintainer Approval Artifact: [Source Ingestion Maintainer Approval Artifact](SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT.md)
- Maintainer Approval Artifact Doc: `docs/SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT.md`
- Maintainer Approval Artifact Module: `src/tuc/frontend/source_ingestion_maintainer_approval.py`
- Maintainer Approval Artifact Example: `examples/source_ingestion_maintainer_approval_artifact.py`
- Maintainer Approval Artifact Schema: `schemas/source_ingestion_maintainer_approval_artifact_report.v0.schema.json`
- Maintainer Approval Artifact Golden: `tests/golden/frontend/source_ingestion_maintainer_approval_artifact_report.json`
- Maintainer Approval Artifact RFC: `rfcs/0269-source-ingestion-maintainer-approval-artifact.md`
- Admitting Source Ingestion RFC: [Admitting Source Ingestion RFC](ADMITTING_SOURCE_INGESTION_RFC.md)
- Real Triton First Slice Plan: [Real Triton First Slice Plan](REAL_TRITON_FIRST_SLICE_PLAN.md)
- Evidence Graph Acyclicity Gate: [Evidence Graph Acyclicity Gate](EVIDENCE_GRAPH_ACYCLICITY_GATE.md)
- Evidence Graph Acyclicity Gate Module: `src/tuc/evidence_graph_acyclicity.py`
- Evidence Graph Acyclicity Gate Example: `examples/evidence_graph_acyclicity_gate.py`
- Evidence Graph Acyclicity Gate Schema: `schemas/evidence_graph_acyclicity_gate_report.v0.schema.json`
- Evidence Graph Acyclicity Gate Golden: `tests/golden/frontend/evidence_graph_acyclicity_gate_report.json`
- Evidence Graph Acyclicity Gate RFC: `rfcs/0270-evidence-graph-acyclicity-gate.md`
