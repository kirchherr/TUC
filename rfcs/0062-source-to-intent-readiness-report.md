# RFC 0062: Source-To-Intent Readiness Report

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC adds a deterministic readiness report for future source-to-intent parser
proposals.

This RFC does not implement a parser, source ingestion, preflight-to-intent
conversion, source-file loading, Python module imports, decorator evaluation,
`@triton.jit` execution, source-to-metadata conversion,
source-to-`ComputeGraph` construction, lowering, runtime planning, backend
selection, plugin discovery, generated-artifact execution, or device access.

This RFC does not add preflight-to-intent conversion.

## Motivation

RFC 0061 defines the Source-To-Intent Parser Gate. Maintainers also need a
stable way to review whether a future parser proposal has every required piece
of evidence before implementation begins.

The readiness report makes missing evidence visible in a deterministic JSON
artifact without accepting source text or third-party parser code.

## Decision

Add `tuc.frontend.source_to_intent_readiness` with:

- `SourceToIntentReadinessEvidence`
- `build_source_to_intent_readiness_report(proposal_name, evidence)`
- `assert_source_to_intent_readiness(proposal_name, evidence)`
- `dump_source_to_intent_readiness_report(report)`
- report schema version `tuc.source_to_intent_readiness_report.v0`
- gate contract `source_to_intent_parser_gate.blocking.v0`

The report is ready only when every required evidence ID is present.

## Required Evidence IDs

The v0 report requires:

- `parser_rfc`
- `parser_threat_model_update`
- `parser_budget_table`
- `accepted_source_corpus`
- `rejected_source_corpus`
- `source_fuzz_or_property_corpus`
- `parser_report_golden`
- `source_intent_plain_data_golden`
- `source_intent_intake_report_golden`
- `source_intent_metadata_report_golden`
- `metadata_intake_report_golden`
- `hac_ir_golden`
- `runtime_plan_golden`
- `compiler_decision_report_golden`
- `hac_ir_neutrality_review`
- `source_intent_frontend_conformance_report`
- `source_intent_frontend_conformance_gate`

## Security Boundary

The readiness report accepts only explicit evidence IDs and booleans. It must
not include raw source text, raw frontend payloads, host paths, environment
data, generated artifacts, plugin entrypoints, device handles, backend
artifacts, cache paths, or source snippets.

The readiness report must not include raw source text.

Unknown evidence IDs and duplicate evidence IDs fail closed.

The report does not validate source payload semantics. Source semantics remain
blocked until a future parser RFC satisfies the Source-To-Intent Parser Gate and
emitted payloads pass Source Intent Intake.

Source semantics remain blocked.

## Evidence

The implementation adds:

- `src/tuc/frontend/source_to_intent_readiness.py`
- `examples/source_to_intent_readiness.py`
- `docs/SOURCE_TO_INTENT_READINESS.md`
- `tests/test_source_to_intent_readiness.py`
- `tests/golden/frontend/source_to_intent_readiness_report.json`

The golden report intentionally remains blocked because no parser proposal has
supplied the required evidence.

## Consequences

- Parser proposals become reviewable before implementation starts.
- Missing evidence is visible and deterministic.
- The source-to-intent gate remains closed until all required evidence exists.

## Rejected Alternatives

1. Track readiness in prose only.

   Rejected because parser readiness needs deterministic review evidence.

2. Allow arbitrary notes or source snippets in readiness reports.

   Rejected because reports must not amplify attacker-controlled source or leak
   host-specific information.

3. Treat partial evidence as enough to start parser implementation.

   Rejected because source text is attacker-controlled input and the gate must
   stay closed until every required artifact exists.
