# Source-To-Intent Research Source Runtime Smoke

Source-To-Intent Research Source Runtime Smoke v0 is the practical end-to-end
smoke path for the current accepted research source buffers.

It proves that the accepted caller-provided Triton-like source buffers can pass:

```text
Triton Source Preflight
    ->
Explicit Research Parser
    ->
source_intent.v0 plain data
    ->
Source Intent Intake
    ->
Metadata Conversion
    ->
HAC-IR and Runtime Plan
    ->
Runtime Executor
    ->
Runtime Reference Correctness
```

It does not approve general Triton source ingestion, production parser use, or
native performance claims.

## Contract

- Smoke contract:
  `source_to_intent_research_source_runtime_smoke.e2e.v0`
- Report schema version:
  `tuc.source_to_intent_research_source_runtime_smoke_report.v0`
- Report schema:
  `schemas/source_to_intent_research_source_runtime_smoke_report.v0.schema.json`
- Example: `examples/source_to_intent_research_source_runtime_smoke.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_source_runtime_smoke.json`
- Tests: `tests/test_source_to_intent_research_source_runtime_smoke.py`
- Digest binding: `examples/source_to_intent_research_evidence_gate.py`
- CI entry: `.github/workflows/ci.yml`

## Accepted Source Buffers

- `research_matmul_elementwise`
- `research_softmax_reduction`

Both cases must:

- pass Preflight as bounded syntax data
- emit only `source_intent.v0` plain data from the parser
- re-enter Source Intent Intake before metadata conversion
- execute on simulator backends only
- pass Runtime Reference Correctness

## Security Boundary

The report is metadata-only. It records digests and status fields, but omits
raw source text, raw Source Intent payloads, tensor values, compiler artifacts,
runtime tensor records, backend binaries, host paths, command lines,
environment variables, device identifiers, exception text, generated code, and
benchmark output.

The smoke path keeps three claims blocked:

- `general_triton_source_ingestion`
- `native_performance_claim`
- `production_parser`

## Review Meaning

This is the current practical source-to-runtime proof slice. It complements
the digest-only Proof Bundle by showing that accepted source buffers can run
through the complete controlled path without turning source parsing into a
general compiler input.
