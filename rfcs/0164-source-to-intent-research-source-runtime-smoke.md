# RFC 0164: Source-To-Intent Research Source Runtime Smoke

## Status

Accepted.

## Context

The Source-to-Intent research proof has digest-bound evidence, Preflight
layering, execution bridge evidence, idiom alignment, and a proof bundle. The
next practical step is one deterministic source-buffer to runtime smoke path
for the currently accepted research slices.

## Decision

Add Source-To-Intent Research Source Runtime Smoke v0.

The smoke path runs the two accepted caller-provided Triton-like source buffers
through:

- Triton Source Preflight
- explicit research parser
- `source_intent.v0` plain-data intake
- metadata conversion
- HAC-IR and runtime planning
- Runtime Executor
- Runtime Reference Correctness

The report is metadata-only and digest-based.

## Security Constraints

The smoke report must not:

- approve general Triton source ingestion
- approve production parser use
- approve native performance claims
- emit raw source text
- emit raw Source Intent payloads
- emit raw tensor values
- embed compiler artifacts
- embed runtime plans as raw text
- include host paths, command lines, environment variables, device IDs, or
  exception text
- execute imports, decorators, `@triton.jit`, plugins, generated artifacts,
  subprocesses, dynamic libraries, network access, or real devices

Accepted source buffers must pass Preflight before the research parser can emit
Source Intent plain data.

## Evidence

- Smoke: `examples/source_to_intent_research_source_runtime_smoke.py`
- Documentation:
  `docs/SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE.md`
- Schema:
  `schemas/source_to_intent_research_source_runtime_smoke_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/source_to_intent_research_source_runtime_smoke.json`
- Tests: `tests/test_source_to_intent_research_source_runtime_smoke.py`
- CI: `.github/workflows/ci.yml`
- Digest binding: `examples/source_to_intent_research_evidence_gate.py`
- Structured validation:
  `assert_source_runtime_smoke_report_contract(...)`

## Consequences

TUC now has one practical research source-buffer to runtime smoke path. This
supports the hardware-independent interface proof without presenting the
research parser as a production Triton frontend.
