# RFC 0031: External Backend Author Test

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Gamma

## Summary

TUC adds an external-style backend author path that simulates a toy backend
proposal without modifying TUC core.

The path covers:

- Schema-versioned capability manifest.
- Explicit manifest loading through `BackendRegistry`.
- Pure-data support diagnostics.
- Compiler planning from capability data only.
- Reusable backend conformance fixtures.
- Trusted in-process lowering of only the compiler-assigned HAC-IR subgraph.

## Motivation

TUC's Universal Compute claim needs an integration path for future hardware
authors. That path must be capability-first and execution-free until a backend
object is explicitly constructed by a trusted test or maintainer.

A runnable external-style test gives maintainers evidence that a backend author
can describe hardware capabilities, receive compiler planning decisions, and
prove lower-time behavior without adding plugin discovery, dynamic imports,
device access, or backend code execution to TUC's compiler boundary.

## Decision

Add:

- `examples/manifests/external_vector_backend.json`
- `examples/external_backend_author_path.py`
- `tests/test_external_backend_author_path.py`

The example backend supports `elementwise` operations, prefers that operation
family, accepts row-major inputs, and declares vector output layout in a
device-SRAM memory domain.

The test verifies that:

- The manifest loads only through explicit paths.
- Registry support diagnostics are pure data.
- The compiler assigns the operation to the external backend capability.
- The produced layout reaches HS-IR and runtime planning.
- `assert_backend_conformance(...)` passes.
- Unsupported operations are rejected at lower time.
- Lowering receives only the assigned HAC-IR subgraph.

## Security Model

Manifest and registry steps are data-only. They do not:

- Discover plugins.
- Import modules.
- Spawn subprocesses.
- Load dynamic libraries.
- Touch devices.
- Execute generated artifacts.

Backend lowering runs only after the example explicitly constructs a trusted
in-process backend object. Lowering validates `capability.supports(operation)`
for every operation before emitting an artifact.

## Consequences

- Backend onboarding has a concrete runnable shape.
- Future backend proposals can copy a small reference pattern.
- Capability data and executable backend objects remain separate.
- TUC core remains protected from third-party plugin execution surfaces.

## Alternatives Considered

1. Add a real plugin interface now.

   Rejected because plugin discovery and execution need a dedicated lifecycle
   RFC, sandbox model, provenance story, and negative tests.

2. Keep backend author guidance as documentation only.

   Rejected because the external path should be executable and testable before
   broad contribution.

3. Make conformance read backend manifests and instantiate backends
   automatically.

   Rejected because automatic instantiation would blur the current safe
   boundary between declarative capability data and trusted executable backend
   objects.

## Follow-Up

1. Add capability schema documentation for error, latency, energy, and
   calibration assumptions.
2. Add conformance report serialization as a reviewable artifact.
3. Extend the external-style path to a second operation family after the proof
   ladder remains stable.
