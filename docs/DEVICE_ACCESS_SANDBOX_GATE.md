# Device Access Sandbox Gate

Device Access Sandbox Gate v0 is the dedicated Real Triton Integration surface
gate for `device_access`.

It defines sandbox requirements for future device access without admitting
device access. The current report is data-only and does not discover devices,
enumerate devices, call driver APIs, allocate device memory, map device memory,
perform direct memory access, launch kernels, execute generated artifacts, run
subprocesses, or load dynamic libraries.

## Contract

- Report schema:
  `schemas/device_access_sandbox_gate_report.v0.schema.json`
- Report schema version:
  `tuc.device_access_sandbox_gate_report.v0`
- Gate contract:
  `device_access_sandbox_gate.data_only.v0`
- Example: `examples/device_access_sandbox_gate.py`
- Golden:
  `tests/golden/frontend/device_access_sandbox_gate_report.json`
- Tests: `tests/test_device_access_sandbox_gate.py`
- RFC: `rfcs/0249-device-access-sandbox-gate.md`

## Meaning

The gate binds digest-only evidence for:

- Real Triton Integration Admission Gate;
- Triton JIT Execution Sandbox Gate;
- Device Access Sandbox Model.

The current status is:

- `gate_status = sandbox_requirements_only`;
- `sandbox_boundary_established = true`;
- `admission_effect = does_not_admit_device_access`;
- `device_access = false`;
- `device_discovery = false`;
- `driver_api_call = false`.

This means TUC has reviewable sandbox requirements for device access, not a
device access implementation.

## Required Controls

The gate requires:

- device access is blocked;
- device discovery and enumeration are blocked;
- device handles are blocked;
- device memory allocation and mapping are blocked;
- direct memory access is blocked;
- driver calls are blocked;
- hardware fingerprints are blocked;
- kernel launch is blocked;
- generated artifact execution is blocked;
- subprocess execution is blocked;
- dynamic library loading is blocked;
- digest-only public evidence;
- sanitized diagnostics only;
- fail-closed violations.

## Security Boundary

The report must not contain device identifiers, device handles, driver
contexts, mapped memory, allocation handles, runtime handles, host paths,
command lines, dynamic library paths, generated code, backend artifacts, raw
timing samples, raw benchmark output, or executable permissions.

Future device access may only move beyond this gate after a separate
implementation RFC defines an actual sandbox, driver mediation, device
provenance, resource budgets, allocation isolation, transfer controls,
negative tests, and maintainer approval.
