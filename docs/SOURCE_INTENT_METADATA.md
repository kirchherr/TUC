# Source Intent Metadata Conversion

Source Intent Metadata Conversion is the execution-free bridge from canonical
Source Intent IR into schema-versioned Triton-like metadata.

It starts from an already constructed `SourceIntentModule`. It does not parse
source text, read preflight reports, import Python modules, inspect function
objects, evaluate decorators, execute `@triton.jit`, discover plugins, access
devices, or touch the network.

It does not parse source text.

## Contract

- Contract: `source_intent_to_metadata.execution_free.v0`
- API: `source_intent_to_triton_metadata(module)`
- Report: `build_source_intent_metadata_report(module)`
- Example: `examples/source_intent_metadata.py`
- Tests: `tests/test_source_intent_metadata.py`

The adapter maps:

- `SourceIntentTensor` to `TritonTensorMetadata`
- source-intent operation families to metadata `OperationKind`
- neutral source-intent hints to `CompilationHints`
- source-intent contract metadata to frontend graph metadata

## Security Boundary

The adapter may produce schema-versioned metadata. It must not produce
`ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, or backend decisions
directly.

It must not produce `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, or
backend decisions directly.

Those artifacts are produced only by the already accepted metadata intake and
compiler pipeline after the converted metadata passes normal validation.

The adapter rejects non-`SourceIntentModule` inputs and has no source-text,
preflight-report, Python-object, plugin, backend, device, or runtime entrypoint.

## Evidence

The conversion is golden-tested through:

```text
tests/golden/frontend/source_intent_metadata_report.txt
tests/golden/frontend/source_intent_metadata_intake.txt
tests/golden/hac_ir/source_intent_metadata_mlp.txt
tests/golden/runtime_plans/source_intent_metadata_mlp.txt
tests/golden/compiler_decisions/source_intent_metadata_mlp.txt
```

This proves that Source Intent IR can reach the existing metadata intake path
without weakening the direct source-ingestion gate.

## Still Blocked

These remain future work:

- source text to Source Intent IR
- preflight report to Source Intent IR
- direct Source Intent IR to `ComputeGraph`
- direct Source Intent IR to TLIR, HAC-IR, HS-IR, runtime plans, or backend
  decisions

Any source-text-to-intent path still requires the Triton source threat model,
parser budgets, corpus, negative tests, deterministic diagnostics, and a
separate security review.
