# Native Backend Execution Security Gate

Native Backend Execution Security Gate v0 is the dedicated Real Triton
Integration surface gate for `native_backend_execution`.

It establishes the security requirements for any future native backend path
without admitting native backend execution. The current report is data-only and
does not load native backends, load plugin ABIs, execute backend plugins,
resolve symbols, make FFI calls, touch unsafe memory, load dynamic libraries,
execute generated artifacts, access devices, launch kernels, or run
subprocesses.

## Contract

- Report schema:
  `schemas/native_backend_execution_security_gate_report.v0.schema.json`
- Report schema version:
  `tuc.native_backend_execution_security_gate_report.v0`
- Gate contract:
  `native_backend_execution_security_gate.data_only.v0`
- Example: `examples/native_backend_execution_security_gate.py`
- Golden:
  `tests/golden/frontend/native_backend_execution_security_gate_report.json`
- Tests: `tests/test_native_backend_execution_security_gate.py`
- RFC: `rfcs/0251-native-backend-execution-security-gate.md`

## Meaning

The gate binds digest-only evidence for:

- Real Triton Integration Admission Gate;
- Generated Artifact Quarantine Gate;
- Device Access Sandbox Gate;
- Backend Plugin Lifecycle Policy;
- Native Backend Execution Security Model.

The current status is:

- `gate_status = security_requirements_only`;
- `security_boundary_established = true`;
- `admission_effect = does_not_admit_native_backend_execution`;
- `native_backend_execution = false`;
- `native_plugin_abi_loading = false`;
- `backend_plugin_execution = false`;
- `symbol_resolution = false`;
- `ffi_call = false`.

This means TUC has reviewable security requirements for native backend
execution, not a native backend execution implementation.

## Required Controls

The gate requires:

- native backend execution is blocked;
- native plugin ABI loading is blocked;
- backend plugin execution is blocked;
- generated artifact execution is blocked;
- dynamic library loading is blocked;
- symbol resolution is blocked;
- FFI calls are blocked;
- unsafe memory access is blocked;
- device access is blocked;
- executable permissions are blocked;
- subprocess execution is blocked;
- capability checks are data-only;
- digest-only public evidence;
- sanitized diagnostics only;
- sandbox requirements before any future implementation;
- maintainer approval before any future promotion;
- fail-closed violations.

## Security Boundary

The report must not contain native backend handles, native plugin handles,
loaded symbols, FFI callables, driver contexts, runtime handles, generated code,
backend artifacts, host paths, command lines, dynamic library paths, device
identifiers, raw timing samples, raw benchmark output, or executable
permissions.

Future native backend support may only move beyond this gate after a separate
implementation RFC defines a sandbox model, ABI boundary, artifact provenance,
capability attestation, path isolation, memory-safety controls, negative tests,
fuzzing, maintainer approval, and a replacement proof that preserves the
metadata-only public evidence boundary.