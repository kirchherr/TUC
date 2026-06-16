# RFC 0163: Source-To-Intent Research Proof Bundle

## Status

Accepted.

## Context

The Source-to-Intent research proof now has multiple focused evidence
artifacts: readiness, conformance, diagnostics, Preflight Bridge, Execution
Bridge, Idiom Alignment, and the Research Evidence Gate. Each is useful on its
own, but reviewers need one stable digest-only entry point for the current
research claim.

## Decision

Add Source-To-Intent Research Proof Bundle v0.

The bundle records digests for the current Source-to-Intent research evidence
chain and validates that the Research Evidence Gate binds the expected
component digests. It does not embed the underlying artifacts.

The bundle claim is `safe_source_to_runtime_research_slice`.

## Security Constraints

The bundle must not:

- emit raw source text
- emit raw Source Intent payloads
- emit raw tensor values
- embed compiler artifacts
- embed runtime plans or backend decisions
- include exception text
- include host paths, command lines, environment variables, or device IDs
- include generated code or benchmark output
- approve production parsing
- approve general Triton source ingestion
- approve native performance claims

The bundle remains digest-only and source-free.

## Evidence

- Bundle: `examples/source_to_intent_research_proof_bundle.py`
- Documentation: `docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md`
- Schema:
  `schemas/source_to_intent_research_proof_bundle_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/source_to_intent_research_proof_bundle.json`
- Tests: `tests/test_source_to_intent_research_proof_bundle.py`
- CI: `.github/workflows/ci.yml`
- Structured validation:
  `assert_proof_bundle_report_contract(...)`

## Consequences

The current research proof becomes easier to review without weakening any
boundary. Future source parser expansions must update the underlying evidence
chain before the proof bundle can continue to pass.
