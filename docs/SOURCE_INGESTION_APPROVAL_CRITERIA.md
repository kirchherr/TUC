# Source Ingestion Approval Criteria

Source Ingestion Approval Criteria v0 defines the objective criteria a
maintainer must review before the first `direct_source_ingestion` slice can be
approved.

It is not an approval and does not admit source ingestion. The current report
keeps:

```text
criteria_status = criteria_defined_not_approved
approval_status = not_approved
admitted = false
source_ingestion_admission_ready = false
```

Run it with:

```bash
python examples/source_ingestion_approval_criteria.py
```

## Criteria

The criteria require the maintainer-review path to confirm:

- bounded source-buffer handling.
- sandbox boundary evidence.
- negative corpus evidence.
- source-free diagnostics.
- plain-data golden output.
- CI replay.
- first-slice plan evidence.
- no raw source, Source Intent payload, runtime handle, host path, or command
  serialization.
- no source-to-ComputeGraph, source-to-HAC-IR, or source-to-runtime-plan output.
- direct source ingestion remains blocked until external approval exists.

## Security Boundary

The report is criteria-only and source-free. It does not serialize source text,
Source Intent payloads, tensor values, runtime handles, host paths, commands,
device identifiers, plugin entrypoints, generated code, backend artifacts,
native benchmark output, or executable artifacts.

It does not import external packages, discover plugins, run Triton JIT, access
devices, load dynamic libraries, spawn subprocesses, touch the network, emit
generated artifacts, approve parser behavior, or grant execution permission.

## Contract

- Module: `src/tuc/frontend/source_ingestion_approval_criteria.py`
- Example: `examples/source_ingestion_approval_criteria.py`
- Schema: `schemas/source_ingestion_approval_criteria_report.v0.schema.json`
- Golden: `tests/golden/frontend/source_ingestion_approval_criteria_report.json`
- Tests: `tests/test_source_ingestion_approval_criteria.py`
- RFC: `rfcs/0268-source-ingestion-approval-criteria.md`
- Maintainer Review Packet:
  [Source Ingestion Maintainer Security Review Packet](SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md)
- Maintainer Approval Artifact:
  [Source Ingestion Maintainer Approval Artifact](SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT.md)
- Maintainer Approval Artifact Module:
  `src/tuc/frontend/source_ingestion_maintainer_approval.py`
- Maintainer Approval Artifact Example:
  `examples/source_ingestion_maintainer_approval_artifact.py`
- Maintainer Approval Artifact Schema:
  `schemas/source_ingestion_maintainer_approval_artifact_report.v0.schema.json`
- Maintainer Approval Artifact Golden:
  `tests/golden/frontend/source_ingestion_maintainer_approval_artifact_report.json`
- Maintainer Approval Artifact RFC:
  `rfcs/0269-source-ingestion-maintainer-approval-artifact.md`
- Admission Gate: [Source Ingestion Admission Gate](SOURCE_INGESTION_ADMISSION_GATE.md)
