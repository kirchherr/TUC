# RFC 0161: Source-To-Intent Research Idiom Alignment

## Status

Accepted.

## Context

The explicit Source-to-Intent research parser now has readiness, conformance,
diagnostics, execution bridge, and digest-bound evidence. That proves a narrow
source-to-runtime slice, but it still needs an explicit scope check against the
Triton-like idioms that TUC already claims as MVP coverage.

Without that check, future parser changes could accidentally imply broader
Triton compatibility than the project has actually proven.

## Decision

Add Source-To-Intent Research Idiom Alignment v0.

The alignment report compares accepted research parser source names and
operation families with the existing Triton Idiom Coverage report. Each
accepted parser slice must map to `metadata_golden_covered` Triton-like idioms
before the source slice can count as accepted research scope.

The report also binds the Source-To-Intent Research Execution Bridge digest, so
the idiom scope and practical runtime evidence stay connected.

## Security Constraints

The alignment report must not:

- parse source text
- serialize raw source text
- serialize raw Source Intent payloads
- serialize raw tensor values
- import Triton or user modules
- evaluate decorators
- execute `@triton.jit`
- discover plugins
- access devices
- run subprocesses
- load dynamic libraries
- execute generated artifacts
- expand the accepted parser scope when an idiom is missing

Unsupported operation families fail the structured contract.

## Evidence

- Alignment: `examples/source_to_intent_research_idiom_alignment.py`
- Documentation: `docs/SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT.md`
- Schema:
  `schemas/source_to_intent_research_idiom_alignment_report.v0.schema.json`
- Golden:
  `tests/golden/frontend/source_to_intent_research_idiom_alignment.json`
- Tests: `tests/test_source_to_intent_research_idiom_alignment.py`
- CI: `.github/workflows/ci.yml`
- Digest binding: `examples/source_to_intent_research_evidence_gate.py`
- Structured validation:
  `assert_research_idiom_alignment_report_contract(...)`

## Consequences

The current research parser proof becomes better scoped: accepted source
slices are tied to already reviewed MVP idioms instead of being treated as a
general Triton compatibility claim.

Future parser expansions must update diagnostics, readiness, execution bridge,
idiom alignment, and the evidence gate before they count as accepted research
parser scope.
