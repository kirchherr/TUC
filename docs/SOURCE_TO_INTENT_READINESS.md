# Source-To-Intent Readiness Report

Source-To-Intent Readiness is a deterministic review report for future parser
proposals.

It does not parse source text, inspect preflight reports, load source files,
import frontend modules, discover plugins, produce `source_intent.v0` payloads,
create `SourceIntentModule`, produce metadata, construct `ComputeGraph`, lower
IR, plan runtime placement, or execute backend artifacts.

## Contract

- Gate contract: `source_to_intent_parser_gate.blocking.v0`
- Report schema version: `tuc.source_to_intent_readiness_report.v0`
- Evidence type: `SourceToIntentReadinessEvidence`
- API: `build_source_to_intent_readiness_report(proposal_name, evidence)`
- Assertion API: `assert_source_to_intent_readiness(proposal_name, evidence)`
- Dump API: `dump_source_to_intent_readiness_report(report)`
- Required evidence IDs: `SOURCE_TO_INTENT_REQUIRED_EVIDENCE`
- Example: `examples/source_to_intent_readiness.py`
- Golden: `tests/golden/frontend/source_to_intent_readiness_report.json`
- Tests: `tests/test_source_to_intent_readiness.py`

The report is ready only when every required evidence ID is present.

## Required Evidence

The readiness report tracks:

- parser RFC
- parser threat model update
- parser budget table
- accepted source corpus
- rejected source corpus
- source fuzz or property corpus
- parser report golden
- emitted `source_intent.v0` plain-data golden
- Source Intent Intake report golden
- Source Intent Metadata Conversion report golden
- metadata intake report golden
- HAC-IR golden
- runtime-plan golden
- compiler decision-report golden
- HAC-IR neutrality review
- Source Intent Frontend Conformance report

Missing evidence keeps parser implementation blocked.

## Security Boundary

The readiness report accepts only explicit evidence IDs and booleans. It must
not include raw source text, raw frontend payloads, host paths, environment
data, generated artifacts, plugin entrypoints, device handles, backend
artifacts, or cache paths.

The readiness report must not include raw source text.

Unknown evidence IDs and duplicate evidence IDs fail closed.

The report preserves the [Source-To-Intent Parser Gate](SOURCE_TO_INTENT_PARSER_GATE.md):
a future parser must not import user modules, evaluate decorators, execute
`@triton.jit`, or produce `ComputeGraph` directly.

A future parser must not evaluate decorators.
A future parser must not execute `@triton.jit`.

## Evidence

The current golden report intentionally remains blocked:

```text
tests/golden/frontend/source_to_intent_readiness_report.json
```

This makes the current roadmap state explicit: TUC has a parser gate and a
readiness report, but no source-to-intent parser implementation.

## Still Blocked

These remain blocked after this report exists:

- implementing a source parser
- accepting source text as compiler input
- converting preflight reports into Source Intent IR
- loading source files by path
- importing frontend packages
- source-to-metadata or source-to-ComputeGraph shortcuts
- executing Triton, Python, generated code, or backend artifacts
