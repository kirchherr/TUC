# Source Intent Frontend Conformance

Source Intent Frontend Conformance is a reusable certification path for tools
that emit `source_intent.v0` plain data.

It checks in-memory frontend-produced data. It does not read files, parse source
text, inspect Python objects, import frontend modules, evaluate decorators,
execute `@triton.jit`, discover plugins, access devices, touch the network,
lower backend code, or execute generated artifacts.

It is not a source parser.

It does not parse source text.

## Contract

- Report schema: `tuc.source_intent_frontend_conformance_report.v0`
- Case type: `SourceIntentFrontendConformanceCase`
- API: `run_source_intent_frontend_conformance(frontend_name, cases)`
- Assertion API: `assert_source_intent_frontend_conformance(frontend_name, cases)`
- Report dump: `dump_source_intent_frontend_conformance_report(report)`
- Example: `examples/source_intent_frontend_conformance.py`
- Golden: `tests/golden/frontend/source_intent_frontend_conformance_report.json`
- Tests: `tests/test_source_intent_conformance.py`

Accepted cases must pass:

- Source Intent Intake through `source_intent_from_mapping(data)`
- Source Intent Metadata Conversion through
  `source_intent_to_triton_metadata(module)`
- Metadata to `ComputeGraph` through the existing metadata adapter
- The neutral compiler pipeline with explicit backend capability data and the
  default `reference-cpu` fallback

Rejected cases must fail closed at Source Intent Intake.

## Security Boundary

The conformance suite accepts only caller-provided in-memory case payloads. It
does not load frontend packages, execute frontend code, inspect source text, or
discover backend plugins.

The suite intentionally reports failure stages and exception types, not raw payload contents.
This keeps conformance artifacts useful for review without turning
attacker-controlled input into diagnostic output.

The conformance suite may produce a deterministic JSON report. It must not become a production source ingestion path, parser shim, plugin certification runtime, or backend execution gate.

## Evidence

The example suite includes:

- one accepted Source Intent MLP plain-data case
- a rejected source-text escape case
- a rejected backend-specific hint escape case
- a rejected unknown tensor reference case

The deterministic report is golden-tested at:

```text
tests/golden/frontend/source_intent_frontend_conformance_report.json
```

This gives external frontend authors a repeatable review artifact before any
future source-text parser targets Source Intent data.

## Still Blocked

These remain future work:

- source text to Source Intent data
- preflight report to Source Intent data
- frontend package loading
- path-based frontend fixture loading
- plugin discovery or backend certification through frontend conformance
- direct Source Intent data to backend lowering or artifact execution

Any source-text-to-intent path still requires parser budgets, source corpus,
negative tests, deterministic diagnostics, security review, and source-intent
goldens.
