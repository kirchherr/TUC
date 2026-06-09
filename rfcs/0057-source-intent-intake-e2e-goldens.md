# RFC 0057: Source Intent Intake End-To-End Goldens

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC adds end-to-end golden artifacts for the schema-versioned Source Intent
Intake path.

This RFC does not add source parsing, preflight-to-intent conversion,
filesystem loading, direct metadata output from intake, direct `ComputeGraph`
construction from intake, plugin discovery, backend execution, or code
execution.

## Motivation

RFC 0055 created Source Intent Intake. RFC 0056 added fuzz and corpus coverage.
The next proof is that accepted plain Source Intent data can flow through the
already reviewed gates:

```text
plain data
    ->
SourceIntentModule
    ->
Source Intent Metadata Conversion
    ->
Triton-like metadata intake
    ->
ComputeGraph
    ->
HAC-IR
    ->
runtime plan
    ->
compiler decision report
```

This proves frontend-originated compute intent without granting source text any
compiler influence.

## Decision

Add golden artifacts for `examples/source_intent_intake.py` data after it passes
through the separate metadata conversion and existing compiler pipeline:

- `tests/golden/hac_ir/source_intent_intake_mlp.txt`
- `tests/golden/runtime_plans/source_intent_intake_mlp.txt`
- `tests/golden/compiler_decisions/source_intent_intake_mlp.txt`

The existing Source Intent Intake test now verifies these artifacts alongside
the frontend intake report, Source Intent module dump, and metadata intake
report.

Source Intent Intake must not produce compiler artifacts directly.

## Consequences

- Source Intent Intake has Level 3 validation evidence beyond frontend dumps.
- The accepted plain-data path is reproducible through HAC-IR and runtime
  planning.
- Source text, preflight reports, and parser outputs remain blocked.

## Rejected Alternatives

1. Compile directly from `source_intent_from_mapping`.

   Rejected because Source Intent Intake must not produce compiler artifacts
   directly.

2. Reuse the Source Intent Metadata Conversion example only.

   Rejected because the plain-data intake path needs independent evidence.

3. Add a source parser for the proof.

   Rejected because source parsing remains blocked.
