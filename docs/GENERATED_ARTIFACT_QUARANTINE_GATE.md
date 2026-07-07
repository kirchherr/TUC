# Generated Artifact Quarantine Gate

Generated Artifact Quarantine Gate v0 is the dedicated Real Triton Integration
surface gate for `generated_artifact_execution`.

It defines quarantine requirements for future generated artifacts without
admitting artifact execution. The current report is data-only and does not emit
backend binaries, write artifacts, load artifacts, grant executable
permissions, access artifact caches, execute generated artifacts, access
devices, launch kernels, run subprocesses, or load dynamic libraries.

## Contract

- Report schema:
  `schemas/generated_artifact_quarantine_gate_report.v0.schema.json`
- Report schema version:
  `tuc.generated_artifact_quarantine_gate_report.v0`
- Gate contract:
  `generated_artifact_quarantine_gate.data_only.v0`
- Example: `examples/generated_artifact_quarantine_gate.py`
- Golden:
  `tests/golden/frontend/generated_artifact_quarantine_gate_report.json`
- Tests: `tests/test_generated_artifact_quarantine_gate.py`
- RFC: `rfcs/0250-generated-artifact-quarantine-gate.md`

## Meaning

The gate binds digest-only evidence for:

- Real Triton Integration Admission Gate;
- Triton JIT Execution Sandbox Gate;
- Device Access Sandbox Gate;
- Generated Artifact Quarantine Model.

The current status is:

- `gate_status = quarantine_requirements_only`;
- `quarantine_boundary_established = true`;
- `admission_effect = does_not_admit_generated_artifact_execution`;
- `generated_artifact_execution = false`;
- `artifact_write = false`;
- `executable_permission_granted = false`.

This means TUC has reviewable quarantine requirements for generated artifacts,
not a generated-artifact implementation.

## Required Controls

The gate requires:

- artifact emission is blocked;
- artifact writes are blocked;
- artifact loads are blocked;
- artifact cache access is blocked;
- artifact provenance is required before any future promotion;
- executable permissions are blocked;
- backend binary emission is blocked;
- generated artifact execution is blocked;
- file-system access is blocked;
- device access is blocked;
- kernel launch is blocked;
- subprocess execution is blocked;
- dynamic library loading is blocked;
- digest-only public evidence;
- quarantine metadata only;
- sanitized diagnostics only;
- fail-closed violations.

## Security Boundary

The report must not contain generated code, backend artifacts, artifact paths,
host paths, command lines, dynamic library paths, device identifiers, runtime
handles, cache locations, raw timing samples, raw benchmark output, or
executable permissions.

Future generated artifact support may only move beyond this gate after a
separate implementation RFC defines artifact provenance, content-addressed
storage, path isolation, executable-bit policy, signature or attestation
requirements, negative tests, and maintainer approval.
