# RFC 0159: Source-To-Intent Research Evidence Gate

## Status

Accepted.

## Context

The research parser proof now has three separate evidence surfaces:

- Source-To-Intent Research Readiness
- Source-To-Intent Research Parser Conformance Gate
- Source-To-Intent Research Diagnostics

Those artifacts are useful independently, but the parser proof is stronger if
the accepted scope, negative diagnostics, and readiness status are bound
together in one CI-facing gate.

## Decision

Add Source-To-Intent Research Evidence Gate v0 at
`examples/source_to_intent_research_evidence_gate.py`.

The gate:

- requires Research Readiness to be ready
- requires `source_to_intent_research_diagnostics` in
  `SOURCE_TO_INTENT_REQUIRED_EVIDENCE`
- requires `source_intent_frontend_conformance_gate` and
  `source_to_intent_research_diagnostics` to be present evidence
- verifies the Research Parser Conformance Gate passes for the accepted parser
  sources
- verifies Research Diagnostics covers the same accepted parser sources and
  all whitelisted rejection reasons
- emits SHA-256 digests for readiness, conformance-gate, and diagnostics
  artifacts

## Security Constraints

The gate must not:

- parse source text
- serialize raw source text
- serialize Source Intent payloads
- serialize raw exception text
- import source modules
- evaluate decorators
- execute `@triton.jit`
- compile bytecode
- read source files by path
- access devices
- run subprocesses
- discover plugins
- lower source directly to metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, a
  runtime plan, or a backend decision

## Evidence

- Gate: `examples/source_to_intent_research_evidence_gate.py`
- Documentation: `docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md`
- Golden: `tests/golden/frontend/source_to_intent_research_evidence_gate.txt`
- Tests: `tests/test_source_to_intent_research_evidence_gate.py`
- CI: `.github/workflows/ci.yml`

## Consequences

The research parser proof is now digest-bound across readiness, conformance,
and diagnostics. Future parser syntax cannot count as accepted research scope
by changing only one artifact; it must update the whole gate chain.

This does not approve default source ingestion or a production parser.
