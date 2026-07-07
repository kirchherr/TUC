# Triton JIT Execution Sandbox Gate

Triton JIT Execution Sandbox Gate v0 is the dedicated Real Triton Integration
surface gate for `triton_jit_execution`.

It defines sandbox requirements for future Triton JIT execution without
admitting JIT execution. The current report is data-only and does not invoke
Triton JIT, launch kernels, execute generated artifacts, access devices, read
or write kernel caches, import frontend packages, import Python modules,
discover plugins, access the network, run subprocesses, or load dynamic
libraries.

## Contract

- Report schema:
  `schemas/triton_jit_execution_sandbox_gate_report.v0.schema.json`
- Report schema version:
  `tuc.triton_jit_execution_sandbox_gate_report.v0`
- Gate contract:
  `triton_jit_execution_sandbox_gate.data_only.v0`
- Example: `examples/triton_jit_execution_sandbox_gate.py`
- Golden:
  `tests/golden/frontend/triton_jit_execution_sandbox_gate_report.json`
- Tests: `tests/test_triton_jit_execution_sandbox_gate.py`
- RFC: `rfcs/0248-triton-jit-execution-sandbox-gate.md`

## Meaning

The gate binds digest-only evidence for:

- Package Import Sandbox Gate;
- Plugin Discovery Allowlist Gate;
- Real Triton Integration Admission Gate;
- Source Ingestion Quarantine Gate;
- Triton JIT Execution Sandbox Model.

The current status is:

- `gate_status = sandbox_requirements_only`;
- `sandbox_boundary_established = true`;
- `admission_effect = does_not_admit_triton_jit_execution`;
- `triton_jit_execution = false`;
- `kernel_launch = false`;
- `device_access = false`.

This means TUC has reviewable sandbox requirements for Triton JIT execution,
not a JIT execution implementation.

## Required Controls

The gate requires:

- source buffers are not executed;
- compilation outputs are metadata-only;
- digest-only public evidence;
- no Triton JIT execution;
- no kernel launch;
- no generated artifact execution;
- no backend binary emission;
- no kernel cache access or cache writes;
- no device access;
- no frontend package import;
- no Python import;
- no plugin discovery;
- no network access;
- no subprocess execution;
- no dynamic library loading;
- entrypoints are not discovered;
- sanitized diagnostics only;
- fail-closed violations.

## Security Boundary

The report must not contain source text, Python source, generated code, backend
artifacts, device identifiers, runtime handles, host paths, command lines,
kernel-cache locations, dynamic library paths, imported modules, plugin
entrypoints, raw benchmark output, raw timing samples, or executable
permissions.

Future Triton JIT execution may only move beyond this gate after a separate
implementation RFC defines an actual sandbox, cache isolation, artifact
provenance, device mediation, resource limits, negative tests, and maintainer
approval.
