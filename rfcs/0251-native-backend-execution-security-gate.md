# RFC 0251: Native Backend Execution Security Gate

## Status

Accepted as a fail-closed data-only surface gate.

## Context

Real Triton Integration Admission identifies
`native_backend_execution_security_gate` as the required gate for the
`native_backend_execution` surface.

Generated Artifact Quarantine Gate and Device Access Sandbox Gate keep generated
artifact execution, device access, kernel launch, subprocess execution, and
dynamic library loading blocked. Backend Plugin Lifecycle Policy keeps external
plugin discovery, artifact execution, and native plugin ABI loading disabled by
default. That still is not enough to allow native backend execution. Native
backends add ABI loading, symbol resolution, FFI calls, unsafe memory access,
plugin execution, driver contexts, executable artifacts, and capability claims
that could come from code rather than reviewed data.

## Decision

Add Native Backend Execution Security Gate v0.

The gate binds digest-only evidence for:

- Real Triton Integration Admission Gate;
- Generated Artifact Quarantine Gate;
- Device Access Sandbox Gate;
- Backend Plugin Lifecycle Policy;
- Native Backend Execution Security Model.

The gate emits only:

- gate status and admission effect;
- required evidence IDs and SHA-256 digests;
- required security controls;
- blocked execution surfaces;
- blocked outputs;
- fixed `false` flags for native backend execution, native backend loading,
  native plugin ABI loading, backend plugin execution, native backend handle
  emission, symbol resolution, FFI calls, unsafe memory access, dynamic library
  loading, generated artifact execution, executable permissions, device access,
  kernel launch, subprocess execution, and capability claims from native code.

## Security Constraints

The gate must not:

- load native backends;
- load plugin ABIs;
- execute backend plugins;
- resolve symbols;
- make FFI calls;
- access unsafe memory;
- load dynamic libraries;
- execute generated artifacts;
- grant executable permissions;
- access devices;
- launch kernels;
- run subprocesses;
- derive capability claims from native code;
- serialize native backend handles, native plugin handles, loaded symbols, FFI
  callables, driver contexts, runtime handles, generated code, backend
  artifacts, host paths, command lines, dynamic library paths, device
  identifiers, raw timing samples, or executable permissions.

Every future native backend execution proposal must preserve this gate or
replace it with a stricter successor RFC and security proof.

## Evidence

- Implementation:
  `src/tuc/frontend/native_backend_execution_security_gate.py`
- Example: `examples/native_backend_execution_security_gate.py`
- Report schema:
  `schemas/native_backend_execution_security_gate_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/native_backend_execution_security_gate_report.json`
- Tests: `tests/test_native_backend_execution_security_gate.py`
- Documentation:
  `docs/NATIVE_BACKEND_EXECUTION_SECURITY_GATE.md`

## Consequences

TUC now has a seventh dedicated Real Triton Integration surface gate. It makes
native backend execution security requirements reviewable while keeping native
backend loading, native plugin ABI loading, backend plugin execution, symbol
resolution, FFI calls, unsafe memory access, dynamic libraries, devices,
kernels, subprocesses, and generated artifact execution closed.