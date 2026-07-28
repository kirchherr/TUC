# Real Triton First Slice Maintainer Approval Request

Real Triton First Slice Maintainer Approval Request v0 is the human-review
handoff packet for the first possible admitting Real Triton slice. It packages
the current readiness, review, approval-absence, and admission-gate evidence
for external maintainer security review without granting that approval.

Run it with:

```bash
python examples/real_triton_first_slice_maintainer_approval_request.py
```

The report is schema-versioned at:

```text
schemas/real_triton_first_slice_maintainer_approval_request_report.v0.schema.json
```

Golden evidence lives at:

```text
tests/golden/frontend/real_triton_first_slice_maintainer_approval_request_report.json
```

## Meaning

The request binds these fixed evidence artifacts by digest:

- Real Triton First Slice Admission Readiness Gate.
- Source Ingestion Maintainer Security Review Packet.
- Source Ingestion Maintainer Approval Artifact.
- Source Ingestion Admission Gate.

The report is ready for external review, but it is not itself approval:

```text
request_status = ready_for_external_review
approval_request_is_approval = false
approval_status = not_approved
admission_ready = false
admitted = false
surface_opened = false
```

This gives reviewers one compact packet to inspect while preserving the core
TUC boundary: no source-ingestion surface opens until a real external maintainer
approval artifact exists.

## Security Boundary

The request reads only fixed repository evidence artifacts and emits only
bounded metadata and SHA-256 digests. It does not execute source, import
frontend packages, discover plugins, run Triton JIT, access devices, load
dynamic libraries, spawn subprocesses, touch the network, emit generated
artifacts, or authorize source-to-ComputeGraph, source-to-HAC-IR, or
source-to-runtime-plan shortcuts.

It does not serialize source text, Source Intent payloads, raw tensor values,
runtime handles, host paths, device identifiers, command lines, backend
artifacts, raw benchmark data, or generated code.

## Contract

- Example: `examples/real_triton_first_slice_maintainer_approval_request.py`
- Schema: `schemas/real_triton_first_slice_maintainer_approval_request_report.v0.schema.json`
- Golden: `tests/golden/frontend/real_triton_first_slice_maintainer_approval_request_report.json`
- Tests: `tests/test_real_triton_first_slice_maintainer_approval_request.py`
- Admission Readiness Gate: `docs/REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE.md`
- Admission Readiness Gate Example: `examples/real_triton_first_slice_admission_readiness_gate.py`
- Admission Readiness Gate Schema: `schemas/real_triton_first_slice_admission_readiness_gate_report.v0.schema.json`
- Admission Readiness Gate Golden: `tests/golden/frontend/real_triton_first_slice_admission_readiness_gate_report.json`
- Maintainer Review Packet: `docs/SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md`
- Maintainer Review Packet Example: `examples/source_ingestion_maintainer_security_review_packet.py`
- Maintainer Review Packet Schema: `schemas/source_ingestion_maintainer_security_review_packet_report.v0.schema.json`
- Maintainer Review Packet Golden: `tests/golden/frontend/source_ingestion_maintainer_security_review_packet_report.json`
- Maintainer Approval Artifact: `docs/SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT.md`
- Maintainer Approval Artifact Example: `examples/source_ingestion_maintainer_approval_artifact.py`
- Maintainer Approval Artifact Schema: `schemas/source_ingestion_maintainer_approval_artifact_report.v0.schema.json`
- Maintainer Approval Artifact Golden: `tests/golden/frontend/source_ingestion_maintainer_approval_artifact_report.json`
- Source Ingestion Admission Gate: `docs/SOURCE_INGESTION_ADMISSION_GATE.md`
- Source Ingestion Admission Gate Example: `examples/source_ingestion_admission_gate.py`
- Source Ingestion Admission Gate Schema: `schemas/source_ingestion_admission_gate_report.v0.schema.json`
- Source Ingestion Admission Gate Golden: `tests/golden/frontend/source_ingestion_admission_gate_report.json`
- RFC: `rfcs/0278-real-triton-first-slice-maintainer-approval-request.md`
