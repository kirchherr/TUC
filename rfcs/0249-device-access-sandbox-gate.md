# RFC 0249: Device Access Sandbox Gate

## Status

Accepted as a fail-closed data-only surface gate.

## Context

Real Triton Integration Admission identifies `device_access_sandbox_gate` as
the required gate for the `device_access` surface.

Triton JIT Execution Sandbox Gate keeps JIT, kernel launch, generated artifact
execution, device access, cache access, and backend binary emission blocked.
That still is not enough to touch real devices. Device access can enumerate
hardware, reveal identifiers, call driver APIs, create opaque handles, allocate
memory, map buffers, transfer data, launch kernels, or load dynamic libraries.

## Decision

Add Device Access Sandbox Gate v0.

The gate binds digest-only evidence for:

- Real Triton Integration Admission Gate;
- Triton JIT Execution Sandbox Gate;
- Device Access Sandbox Model.

The gate emits only:

- gate status and admission effect;
- required evidence IDs and SHA-256 digests;
- required sandbox controls;
- blocked execution surfaces;
- blocked outputs;
- fixed `false` flags for device access, device discovery, device
  enumeration, device handle emission, device memory allocation, device memory
  mapping, direct memory access, driver API calls, hardware fingerprint
  serialization, kernel launch, generated artifact execution, Triton JIT
  execution, subprocess execution, and dynamic library loading.

## Security Constraints

The gate must not:

- access devices;
- discover or enumerate devices;
- call driver APIs;
- emit device handles;
- allocate device memory;
- map device memory;
- perform direct memory access;
- serialize hardware fingerprints;
- launch kernels;
- execute generated artifacts;
- invoke Triton JIT;
- run subprocesses;
- load dynamic libraries;
- serialize device identifiers, device handles, driver contexts, mapped memory,
  allocation handles, runtime handles, host paths, command lines, generated
  code, backend artifacts, raw timing samples, or executable permissions.

Every future device access proposal must preserve this gate or replace it with
a stricter successor RFC and sandbox proof.

## Evidence

- Implementation:
  `src/tuc/frontend/device_access_sandbox_gate.py`
- Example: `examples/device_access_sandbox_gate.py`
- Report schema:
  `schemas/device_access_sandbox_gate_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/device_access_sandbox_gate_report.json`
- Tests: `tests/test_device_access_sandbox_gate.py`
- Documentation:
  `docs/DEVICE_ACCESS_SANDBOX_GATE.md`

## Consequences

TUC now has a fifth dedicated Real Triton Integration surface gate. It makes
device access sandbox requirements reviewable while keeping real devices,
driver APIs, device handles, device memory, direct memory access, and kernel
launch closed.
