# Source Intent Intake

Source Intent Intake is the schema-versioned plain-data entrypoint for
canonical Source Intent IR.

It accepts already decoded JSON-like data. It does not read files, parse source
text, inspect Python objects, import modules, evaluate decorators, execute
`@triton.jit`, discover plugins, access devices, touch the network, or produce
compiler artifacts.

It does not parse source text.

## Contract

- Schema: `source_intent.v0`
- Intake contract: `source_intent_intake.execution_free.v0`
- API: `source_intent_from_mapping(data)`
- Report: `build_source_intent_intake_report(module)`
- JSON Schema: `schemas/source_intent.v0.schema.json`
- Example: `examples/source_intent_intake.py`
- Tests: `tests/test_source_intent_intake.py`
- Seed corpus: `tests/corpus/source_intent_intake/`
- Property tests: `tests/test_source_intent_intake_fuzz.py`

Accepted plain data:

- top-level `name`, `schema_version`, `tensors`, and `operations`
- tensor `name`, `shape`, and optional `dtype`
- operation `name`, `family`, `inputs`, `outputs`, and optional `hints`
- neutral source-intent hints already accepted by Source Intent IR

Unsupported keys fail closed.

The machine-readable schema is documented in
[Source Intent JSON Schema](SOURCE_INTENT_SCHEMA.md). The schema is an
interoperability artifact; the trusted runtime boundary remains
`source_intent_from_mapping(data)`.

## Security Boundary

Source Intent Intake may produce a `SourceIntentModule`.

It must not produce metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime
plans, or backend decisions directly. Those artifacts require the separate
Source Intent Metadata Conversion adapter and the existing compiler pipeline.

It must not accept source text or preflight reports. It accepts only plain
mapping data supplied by a caller that has already decoded and bounded the
input.

## Evidence

The intake is golden-tested through:

```text
tests/golden/frontend/source_intent_intake_report.txt
tests/golden/frontend/source_intent_intake_module.txt
tests/golden/frontend/source_intent_intake_metadata.txt
tests/golden/hac_ir/source_intent_intake_mlp.txt
tests/golden/runtime_plans/source_intent_intake_mlp.txt
tests/golden/compiler_decisions/source_intent_intake_mlp.txt
```

The HAC-IR, runtime-plan, and compiler decision-report goldens are produced
only after the separate Source Intent Metadata Conversion adapter and existing
metadata intake path validate the module. Source Intent Intake itself still
does not produce compiler artifacts directly.

The intake also has property-test and seed-corpus coverage for:

- arbitrary JSON-like values
- seed payload wrapping
- unsupported schema versions
- unknown source-text fields
- backend-specific hint escape attempts
- unknown tensor references

This gives future source parsers a stable target data shape without granting
source text any compiler influence today.

## Still Blocked

These remain future work:

- source text to Source Intent data
- preflight report to Source Intent data
- filesystem or path-based loading helpers
- direct Source Intent Intake to metadata or compiler artifacts

Any source-text-to-intent path still requires parser budgets, source corpus,
negative tests, deterministic diagnostics, security review, and source-intent
goldens.

[Source-To-Intent Parser Gate](SOURCE_TO_INTENT_PARSER_GATE.md) is the required
future gate before source text or preflight reports may create
`source_intent.v0` plain data for this intake.
