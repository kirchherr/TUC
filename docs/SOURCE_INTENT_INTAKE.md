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
- Example: `examples/source_intent_intake.py`
- Tests: `tests/test_source_intent_intake.py`

Accepted plain data:

- top-level `name`, `schema_version`, `tensors`, and `operations`
- tensor `name`, `shape`, and optional `dtype`
- operation `name`, `family`, `inputs`, `outputs`, and optional `hints`
- neutral source-intent hints already accepted by Source Intent IR

Unsupported keys fail closed.

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
```

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
