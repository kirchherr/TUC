# RFC 0250: Generated Artifact Quarantine Gate

## Status

Accepted as a fail-closed data-only surface gate.

## Context

Real Triton Integration Admission identifies
`generated_artifact_quarantine_gate` as the required gate for the
`generated_artifact_execution` surface.

Triton JIT Execution Sandbox Gate and Device Access Sandbox Gate keep JIT,
kernel launch, device access, cache access, backend binary emission, and
generated artifact execution blocked. That still is not enough to allow
generated artifacts. Generated artifacts can carry executable code, host paths,
cache locations, dynamic library references, driver assumptions, and
provenance requirements.

## Decision

Add Generated Artifact Quarantine Gate v0.

The gate binds digest-only evidence for:

- Real Triton Integration Admission Gate;
- Triton JIT Execution Sandbox Gate;
- Device Access Sandbox Gate;
- Generated Artifact Quarantine Model.

The gate emits only:

- gate status and admission effect;
- required evidence IDs and SHA-256 digests;
- required quarantine controls;
- blocked execution surfaces;
- blocked outputs;
- fixed `false` flags for generated artifact execution, generated artifact
  emission, artifact writes, artifact loads, artifact cache access, artifact
  provenance verification, executable permissions, backend binary emission,
  compiled-kernel emission, file-system access, device access, kernel launch,
  Triton JIT execution, subprocess execution, and dynamic library loading.

## Security Constraints

The gate must not:

- emit generated artifacts;
- write artifacts to disk;
- load artifacts;
- grant executable permissions;
- read or write artifact caches;
- emit backend binaries or compiled kernels;
- execute generated artifacts;
- access filesystems or host paths;
- access devices;
- launch kernels;
- invoke Triton JIT;
- run subprocesses;
- load dynamic libraries;
- serialize generated code, backend artifacts, artifact paths, host paths,
  command lines, dynamic library paths, device identifiers, runtime handles,
  cache locations, raw timing samples, or executable permissions.

Every future generated artifact proposal must preserve this gate or replace it
with a stricter successor RFC and quarantine proof.

## Evidence

- Implementation:
  `src/tuc/frontend/generated_artifact_quarantine_gate.py`
- Example: `examples/generated_artifact_quarantine_gate.py`
- Report schema:
  `schemas/generated_artifact_quarantine_gate_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/generated_artifact_quarantine_gate_report.json`
- Tests: `tests/test_generated_artifact_quarantine_gate.py`
- Documentation:
  `docs/GENERATED_ARTIFACT_QUARANTINE_GATE.md`

## Consequences

TUC now has a sixth dedicated Real Triton Integration surface gate. It makes
generated artifact quarantine requirements reviewable while keeping artifact
emission, artifact writes, artifact loading, executable permissions, backend
binaries, and generated artifact execution closed.
