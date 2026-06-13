# Source-To-Intent Research Preflight Bridge

Source-To-Intent Research Preflight Bridge v0 proves that the explicit
research parser diagnostics are gated by execution-free Triton Source
Preflight before parser semantics can matter.

It does not enable the default source parser path and does not approve general
Triton source ingestion.

## Contract

- Bridge contract:
  `source_to_intent_research_preflight_bridge.execution_free.v0`
- Report schema version:
  `tuc.source_to_intent_research_preflight_bridge_report.v0`
- Report schema:
  `schemas/source_to_intent_research_preflight_bridge_report.v0.schema.json`
- Example: `examples/source_to_intent_research_preflight_bridge.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_preflight_bridge.json`
- Tests: `tests/test_source_to_intent_research_preflight_bridge.py`
- Digest binding: `examples/source_to_intent_research_evidence_gate.py`
- CI entry: `.github/workflows/ci.yml`

## What It Proves

For the six current research diagnostic cases, the bridge separates three
outcomes:

- `accepted_pipeline`: Preflight accepts and the parser diagnostic accepts.
- `preflight_reject`: Preflight rejects before parser semantics can approve
  anything.
- `parser_semantic_reject`: Preflight accepts bounded syntax, but parser
  semantics reject unsupported or ambiguous source intent.

Current counts:

- accepted pipeline cases: 2
- preflight reject cases: 2
- parser semantic reject cases: 2

## Security Boundary

The bridge report is metadata-only. It records source digests, report-safe case
IDs, preflight status, rejected feature IDs, parser diagnostic outcomes, and
operation families. It does not emit raw source text, Source Intent payloads,
compiler artifacts, runtime plans, backend decisions, tensor values, exception
text, file paths, command lines, environment variables, or device identifiers.

The bridge keeps Source Preflight as the first source-text boundary. Parser
semantic rejection is allowed only after Preflight has accepted the source as
bounded syntax data.

## Review Meaning

This report makes the source intake chain easier to audit:

```text
source buffer
    ->
Triton Source Preflight
    ->
explicit research parser diagnostics
    ->
source-free preflight bridge evidence
```

Future parser expansions must preserve this layering before they can count as
accepted research parser scope.
