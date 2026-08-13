# RFC 0248: Triton JIT Execution Sandbox Gate

## Status

Accepted as a fail-closed data-only surface gate.

## Context

Real Triton Integration Admission identifies
`triton_jit_execution_sandbox_gate` as the required gate for the
`triton_jit_execution` surface.

Source Ingestion Quarantine Gate, Package Import Sandbox Gate, and Plugin
Discovery Allowlist Gate prove that source buffers, packages, and plugin
surfaces can be kept closed as reviewed data-only evidence. That is not enough
to invoke Triton JIT. JIT execution can compile kernels, launch device work,
write caches, emit backend binaries, load dynamic libraries, start
subprocesses, or create executable artifacts.

## Decision

Add Triton JIT Execution Sandbox Gate v0.

The gate binds digest-only evidence for:

- Package Import Sandbox Gate;
- Plugin Discovery Allowlist Gate;
- Real Triton Integration Admission Gate;
- Source Ingestion Quarantine Gate;
- Triton JIT Execution Sandbox Model.

The gate emits only:

- gate status and admission effect;
- required evidence IDs and SHA-256 digests;
- required sandbox controls;
- blocked execution surfaces;
- blocked outputs;
- fixed `false` flags for Triton JIT execution, kernel launch, generated
  artifact execution, device access, kernel-cache access, backend binary
  emission, compiled-kernel emission, source execution, package import, Python
  import, plugin discovery, network access, subprocess execution, and dynamic
  library loading.

## Security Constraints

The gate must not:

- invoke Triton JIT;
- launch kernels;
- execute generated artifacts;
- access devices;
- read or write kernel caches;
- emit backend binaries or compiled kernels;
- execute source buffers;
- import frontend packages;
- import Python modules;
- discover plugins or entrypoints;
- access the network;
- run subprocesses;
- load dynamic libraries;
- serialize source text, Python source, generated code, backend artifacts,
  device identifiers, runtime handles, host paths, command lines, cache paths,
  imported modules, plugin entrypoints, raw timing samples, or executable
  permissions.

Every future Triton JIT proposal must preserve this gate or replace it with a
stricter successor RFC and sandbox proof.

## Evidence

- Implementation:
  `src/tuc/frontend/triton_jit_execution_sandbox_gate.py`
- Example: `examples/triton_jit_execution_sandbox_gate.py`
- Report schema:
  `schemas/triton_jit_execution_sandbox_gate_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/triton_jit_execution_sandbox_gate_report.json`
- Tests: `tests/test_triton_jit_execution_sandbox_gate.py`
- Documentation:
  `docs/TRITON_JIT_EXECUTION_SANDBOX_GATE.md`

## Consequences

TUC now has a fourth dedicated Real Triton Integration surface gate. It makes
Triton JIT sandbox requirements reviewable while keeping real JIT execution,
kernel launch, device access, cache mutation, and executable artifacts closed.
