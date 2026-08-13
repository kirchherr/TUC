# RFC 0245: Source Ingestion Quarantine Gate

## Status

Accepted as a fail-closed data-only surface gate.

## Context

Real Triton Integration Admission identifies `source_ingestion_quarantine_gate`
as the required gate for the `direct_source_ingestion` surface. This surface is
one of the highest-risk boundaries in TUC: source buffers may contain hostile
syntax, resource-exhaustion attempts, import tricks, decorator side effects,
JIT triggers, path references, or diagnostic-leakage traps.

TUC needs a dedicated gate before any real source-ingestion work can be
reviewed.

## Decision

Add Source Ingestion Quarantine Gate v0.

The gate binds digest-only evidence for:

- Real Triton Integration Admission Gate;
- Source-To-Intent Parser Gate;
- Triton Source Preflight;
- Triton Source Threat Model.

The gate emits only:

- gate status and admission effect;
- required evidence IDs and SHA-256 digests;
- required quarantine controls;
- blocked execution surfaces;
- blocked compiler outputs;
- fixed `false` flags for direct source ingestion, source-to-ComputeGraph,
  source-to-HAC-IR, source-to-runtime-plan, Python import, function-object
  inspection, Triton JIT, raw source serialization, and generated artifact
  execution.

## Security Constraints

The gate must not:

- import Python packages;
- inspect Python function objects;
- evaluate decorators;
- execute source;
- execute Triton JIT;
- access devices;
- discover plugins;
- emit `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, backend decisions,
  backend artifacts, generated artifacts, raw source, host paths, command
  lines, environment variables, device identifiers, runtime handles, raw timing
  samples, or executable permissions.

Every future source parser expansion must preserve this gate or replace it with
a stricter successor RFC.

## Evidence

- Implementation:
  `src/tuc/frontend/source_ingestion_quarantine_gate.py`
- Example: `examples/source_ingestion_quarantine_gate.py`
- Report schema:
  `schemas/source_ingestion_quarantine_gate_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/source_ingestion_quarantine_gate_report.json`
- Tests: `tests/test_source_ingestion_quarantine_gate.py`
- Documentation:
  `docs/SOURCE_INGESTION_QUARANTINE_GATE.md`

## Consequences

Real Triton Integration now has its first dedicated surface gate. This is
progress toward real integration, but it does not admit direct source ingestion.
It makes the source boundary reviewable before any broader parser, import, JIT,
device, generated-artifact, or native backend surface can open.
