# RFC 0252: Real Triton Surface Gate Completion

## Status

Accepted as a fail-closed data-only completion report.

## Context

Real Triton Integration now has seven dedicated non-admitting surface gates:

- Source Ingestion Quarantine Gate;
- Package Import Sandbox Gate;
- Plugin Discovery Allowlist Gate;
- Triton JIT Execution Sandbox Gate;
- Device Access Sandbox Gate;
- Generated Artifact Quarantine Gate;
- Native Backend Execution Security Gate.

Each gate is useful on its own, but reviewers need a single artifact that shows
the complete perimeter and makes the key point explicit: completion of the gate
set is not admission to execute.

## Decision

Add Real Triton Surface Gate Completion v0.

The completion report binds digest-only evidence for the Real Triton Integration
Admission Gate and all seven surface-gate reports. It emits only:

- completion status;
- blocked admission status;
- required surface-gate IDs;
- surface-gate metadata and SHA-256 digests;
- blocked Real Triton surfaces and claims;
- fixed `false` admission state.

The report does not emit source text, Python source, function objects, host
paths, command lines, environment values, device identifiers, runtime handles,
backend artifacts, generated code, plugin entrypoints, raw benchmark output,
raw timing samples, loaded symbols, FFI callables, or executable permissions.

## Evidence

- Implementation:
  `src/tuc/frontend/real_triton_surface_gate_completion.py`
- Example: `examples/real_triton_surface_gate_completion.py`
- Report schema:
  `schemas/real_triton_surface_gate_completion_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/real_triton_surface_gate_completion_report.json`
- Tests: `tests/test_real_triton_surface_gate_completion.py`
- Documentation:
  `docs/REAL_TRITON_SURFACE_GATE_COMPLETION.md`

## Consequences

TUC now has one compact, machine-readable Real Triton surface-gate completion
artifact. It improves reviewability and roadmap orientation while preserving the
current security boundary: Real Triton integration remains blocked until a
future implementation RFC replaces a specific non-admitting surface gate with a
stronger proof.