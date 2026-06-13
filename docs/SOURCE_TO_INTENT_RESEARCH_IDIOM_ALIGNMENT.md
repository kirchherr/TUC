# Source-To-Intent Research Idiom Alignment

Source-To-Intent Research Idiom Alignment v0 proves that the currently
accepted explicit research parser slices stay inside the already covered
Triton-like MVP idiom scope.

It does not approve general Triton source ingestion and does not expand parser
syntax.

## Contract

- Alignment contract:
  `source_to_intent_research_idiom_alignment.scope.v0`
- Report schema version:
  `tuc.source_to_intent_research_idiom_alignment_report.v0`
- Report schema:
  `schemas/source_to_intent_research_idiom_alignment_report.v0.schema.json`
- Example: `examples/source_to_intent_research_idiom_alignment.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_idiom_alignment.json`
- Tests: `tests/test_source_to_intent_research_idiom_alignment.py`
- Digest binding: `examples/source_to_intent_research_evidence_gate.py`
- CI entry: `.github/workflows/ci.yml`

The example exposes
`assert_research_idiom_alignment_report_contract(...)`. The Research Evidence
Gate validates this structured report before binding its digest.

## What It Proves

The report aligns:

- accepted research parser source names
- emitted operation families
- covered Triton-like metadata idioms
- the Triton Idiom Coverage report digest
- the Source-To-Intent Research Execution Bridge digest

The current accepted alignment is:

- `research_matmul_elementwise`
  - `elementwise`
  - `matmul`
- `research_softmax_reduction`
  - `reduction`
  - `softmax`

Each operation family must match a `metadata_golden_covered` Triton idiom from
the existing Triton Idiom Coverage report.

## Security Boundary

The alignment report is metadata-only. It does not parse source text, import
Triton, evaluate decorators, execute `@triton.jit`, discover plugins, access
devices, run subprocesses, load dynamic libraries, execute generated artifacts,
or emit raw Source Intent payloads or tensor values.

The report stays intentionally conservative: unsupported operation families
make the structured contract fail instead of silently expanding the parser
scope.

## Review Meaning

This report is a scope-control proof. It connects the first accepted
source-to-intent research parser slices to the already reviewed Triton-like MVP
idioms before any broader source syntax work can claim coverage.
