# RFC 0244: Real Triton Integration Admission Gate

## Status

Accepted as a fail-closed data-only frontend security gate.

## Context

Triton Integration Readiness can now be `ready` as review evidence. That is
useful, but it must not be confused with permission to import packages, parse
arbitrary source into compiler artifacts, run Triton JIT, access devices, or
execute backend artifacts.

Real Triton Integration introduces several separate trust boundaries. Treating
them as one milestone would hide the most important security work.

## Decision

Add Real Triton Integration Admission Gate v0.

The gate accepts only digest-bound evidence for:

- External Frontend Package Conformance;
- Real Triton Integration Threat Model;
- Triton Integration Readiness.

The gate emits:

- admission contract and status;
- `admitted = false`;
- required evidence IDs and digests;
- blocked real integration surfaces;
- future surface gate IDs;
- blocked claims;
- fixed `false` flags for source ingestion, frontend package import, plugin
  discovery, Triton JIT execution, device access, generated artifact
  execution, and native backend execution.

## Security Constraints

The gate must not:

- import external frontend packages;
- perform Python imports for candidate packages;
- discover plugins or entrypoints;
- inspect Python function objects;
- ingest arbitrary Triton source into compiler artifacts;
- execute `@triton.jit`;
- access devices;
- load dynamic libraries;
- run subprocesses;
- access the network;
- execute generated or backend artifacts;
- serialize raw source, host paths, command lines, environment variables,
  device identifiers, runtime handles, generated code, backend artifacts, raw
  benchmark output, or raw timing samples.

Each blocked surface requires a separate RFC and gate before admission can
change.

## Evidence

- Implementation:
  `src/tuc/frontend/real_triton_integration_admission.py`
- Example: `examples/real_triton_integration_admission_gate.py`
- Report schema:
  `schemas/real_triton_integration_admission_gate_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/real_triton_integration_admission_gate_report.json`
- Tests: `tests/test_real_triton_integration_admission_gate.py`
- Documentation:
  `docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md`
- Threat model:
  `docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md`

## Consequences

TUC can now say that Real Triton Integration readiness is evidence-complete
while Real Triton Integration admission remains blocked.

This keeps the research path credible and secure: progress is visible, but no
new execution, import, plugin, device, or native backend surface is silently
opened.
