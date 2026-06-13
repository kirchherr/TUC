# RFC 0162: Source-To-Intent Research Preflight Bridge

## Status

Accepted.

## Context

The explicit Source-to-Intent research parser already invokes execution-free
Triton Source Preflight before parsing accepted source buffers as bounded AST
data. That layering is security-critical, but the research evidence chain did
not yet expose the relationship between Preflight outcomes and parser
diagnostic outcomes as its own machine-readable artifact.

## Decision

Add Source-To-Intent Research Preflight Bridge v0.

The report runs the existing research diagnostic cases through Triton Source
Preflight and compares the result with source-free parser diagnostics. It
classifies each case as:

- `accepted_pipeline`
- `preflight_reject`
- `parser_semantic_reject`

The report is metadata-only and emits only bounded IDs, source digests,
operation-family IDs, rejection IDs, and aggregate counts.

## Security Constraints

The bridge must not:

- emit raw source text
- emit raw Source Intent payloads
- emit metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, or backend
  decisions
- emit raw tensor values
- include exception text
- read source files by path
- import Triton or user modules
- evaluate decorators
- execute `@triton.jit`
- discover plugins
- access devices
- run subprocesses
- load dynamic libraries
- execute generated artifacts

Preflight rejection must remain distinguishable from parser semantic rejection.

## Evidence

- Bridge: `examples/source_to_intent_research_preflight_bridge.py`
- Documentation: `docs/SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE.md`
- Schema:
  `schemas/source_to_intent_research_preflight_bridge_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/source_to_intent_research_preflight_bridge.json`
- Tests: `tests/test_source_to_intent_research_preflight_bridge.py`
- CI: `.github/workflows/ci.yml`
- Digest binding: `examples/source_to_intent_research_evidence_gate.py`
- Structured validation:
  `assert_preflight_bridge_report_contract(...)`

## Consequences

The research parser proof becomes more practical and easier to audit: source
syntax must first survive Preflight as bounded data before parser semantics can
emit `source_intent.v0` plain data or reject ambiguous intent.

Future parser expansions must update diagnostics, Preflight bridge evidence,
execution bridge evidence, idiom alignment, and the evidence gate before they
count as accepted research parser scope.
