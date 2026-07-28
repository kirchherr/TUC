# Source Ingestion Maintainer Approval Artifact

Source Ingestion Maintainer Approval Artifact v0 records the current approval
state for the first `direct_source_ingestion` slice.

It is not an approval and does not admit source ingestion. The current report
keeps:

```text
status = external_approval_not_supplied
approval_status = not_approved
approval_artifact_present = false
source_ingestion_admission_ready = false
```

Run it with:

```bash
python examples/source_ingestion_maintainer_approval_artifact.py
```

## What It Binds

The artifact binds the Source Ingestion Maintainer Security Review Packet by
SHA-256 metadata digest and verifies that the packet already contains Source
Ingestion Approval Criteria evidence.

## Meaning

This artifact separates three states that must not be confused:

- approval criteria are defined;
- the maintainer-review packet is ready;
- external maintainer approval is still not supplied.

The Source Ingestion Admission Gate binds this artifact and remains fail-closed
while `approval_artifact_present = false`.

The Real Triton First Slice Maintainer Approval Request also binds this missing
approval state so an external reviewer can see that the request is not an
approval artifact.

## Security Boundary

The report is digest-only and source-free. It does not serialize source text,
Source Intent payloads, tensor values, runtime handles, host paths, command
lines, device identifiers, plugin entrypoints, generated code, backend
artifacts, native benchmark output, or executable artifacts.

It does not import external packages, discover plugins, run Triton JIT, access
devices, load dynamic libraries, spawn subprocesses, touch the network, emit
generated artifacts, approve parser behavior, or grant execution permission.

## Contract

- Module: `src/tuc/frontend/source_ingestion_maintainer_approval.py`
- Example: `examples/source_ingestion_maintainer_approval_artifact.py`
- Schema: `schemas/source_ingestion_maintainer_approval_artifact_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_ingestion_maintainer_approval_artifact_report.json`
- Tests: `tests/test_source_ingestion_maintainer_approval_artifact.py`
- RFC: `rfcs/0269-source-ingestion-maintainer-approval-artifact.md`
- Approval Criteria:
  [Source Ingestion Approval Criteria](SOURCE_INGESTION_APPROVAL_CRITERIA.md)
- Maintainer Review Packet:
  [Source Ingestion Maintainer Security Review Packet](SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md)
- Admission Gate: [Source Ingestion Admission Gate](SOURCE_INGESTION_ADMISSION_GATE.md)
- Real Triton First Slice Maintainer Approval Request: `docs/REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST.md`
- Real Triton First Slice Maintainer Approval Request Example: `examples/real_triton_first_slice_maintainer_approval_request.py`
- Real Triton First Slice Maintainer Approval Request Schema: `schemas/real_triton_first_slice_maintainer_approval_request_report.v0.schema.json`
- Real Triton First Slice Maintainer Approval Request Golden: `tests/golden/frontend/real_triton_first_slice_maintainer_approval_request_report.json`
- Real Triton First Slice Maintainer Approval Request RFC: `rfcs/0278-real-triton-first-slice-maintainer-approval-request.md`
