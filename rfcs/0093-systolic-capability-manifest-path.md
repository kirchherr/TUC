# RFC 0093: Systolic Capability Manifest Path

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Gamma

## Summary

Add a declarative capability manifest for `systolic-sim` and a runnable proof
that uses only explicit manifest-loaded capability data for compiler planning.

## Motivation

The systolic simulator proves that TUC can target another accelerator class,
but future hardware authors also need a path that starts with hardware
self-description rather than in-repository Python objects. This RFC adds that
path for the existing systolic capability while keeping execution authorization
inside the trusted Runtime Executor registry.

## Decision

Add:

- `examples/manifests/systolic_sim_backend.json`
- `examples/systolic_manifest_path.py`
- `tests/golden/proofs/systolic_manifest_path.txt`
- focused manifest, planning, readiness, execution, and golden tests

The manifest declares `systolic-sim` as a `matmul` backend with `device_sram`
outputs and `blocked` produced layout. The example loads that manifest through
`BackendRegistry.from_manifest_paths(...)`, compiles a `matmul -> elementwise`
graph, executes through trusted runtime contracts, and compares the result
against independent reference semantics.

## Security Model

This is a data-only capability path. Manifest loading is bounded,
schema-versioned, duplicate-key rejecting, and unknown-field rejecting.

The manifest does not contain import paths, shell commands, device paths,
dynamic-library names, executable artifact locations, backend source, or
network locations. It can influence compiler planning only as capability data.

Runtime execution remains gated by `runtime_execution_readiness_report(...)`
and the fixed trusted Runtime Executor registry. A manifest can name a backend,
but it cannot make that backend executable unless the trusted registry already
contains a matching executor contract.

## Consequences

- TUC now has a specialized accelerator capability path that begins as
  external-style JSON data.
- `systolic-sim` is demonstrated both as a trusted simulator object and as a
  manifest-loaded planning capability.
- The Universal Compute claim is stronger because hardware self-description can
  guide placement without putting hardware-specific details into HAC-IR.
- No plugin discovery, dynamic import, subprocess execution, device access, JIT,
  network access, dynamic-library loading, or generated-artifact execution is
  introduced.

## References

- [Backend API v0.1](../docs/BACKEND_API.md)
- [Systolic Simulator Proof](../docs/SYSTOLIC_SIMULATOR.md)
- [Runtime Executor v0](../docs/RUNTIME_EXECUTOR.md)
- `examples/systolic_manifest_path.py`
- `examples/manifests/systolic_sim_backend.json`
