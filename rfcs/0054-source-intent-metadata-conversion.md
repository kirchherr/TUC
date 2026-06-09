# RFC 0054: Source Intent Metadata Conversion

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC adds an execution-free adapter from canonical Source Intent IR to
schema-versioned Triton-like metadata.

This RFC does not add source parsing, preflight-to-intent conversion,
Python-object ingestion, direct `ComputeGraph` construction, TLIR lowering,
HAC-IR lowering, runtime planning, backend selection, plugin discovery, or code
execution.

The new contract is:

```text
source_intent_to_metadata.execution_free.v0
```

## Motivation

RFC 0053 introduced Source Intent IR as a data-only frontend contract. The next
reviewable step is to prove that already constructed source intent can flow
into the existing schema-versioned metadata intake without opening a direct
source-ingestion surface.

This keeps the path aligned with the master plan:

```text
compute intent
    ->
source intent
    ->
schema-versioned metadata
    ->
HAC-IR
    ->
runtime planning
```

## Decision

Add `tuc.frontend.source_intent_metadata` with:

- `SOURCE_INTENT_METADATA_CONTRACT`
- `SourceIntentMetadataReport`
- `source_intent_to_triton_metadata`
- `build_source_intent_metadata_report`

The adapter maps Source Intent tensors, operation families, and neutral hints
into `TritonKernelMetadata`.

## Accepted Scope

The adapter may:

- accept an already validated `SourceIntentModule`
- emit schema-versioned `TritonKernelMetadata`
- emit deterministic conversion evidence
- preserve source-intent contract metadata for later review
- rely on the existing metadata adapter to create `ComputeGraph`

## Rejected Scope

The adapter must not:

- parse source text
- consume preflight reports
- import user modules
- inspect Python function objects
- evaluate decorators
- execute `@triton.jit`
- discover plugins or backends
- access devices, files, environment variables, network resources, or
  subprocesses
- produce `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, or backend
  decisions directly

The adapter must not produce `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans,
or backend decisions directly.

## Evidence

The implementation adds:

- conversion unit tests
- non-module rejection tests
- tests proving `SourceIntentModule` still has no conversion method
- deterministic conversion report golden
- deterministic metadata intake report golden
- HAC-IR golden from converted metadata
- runtime-plan golden from converted metadata
- compiler decision-report golden from converted metadata
- documentation in `docs/SOURCE_INTENT_METADATA.md`

## Consequences

- TUC now has a controlled proof that canonical source intent can enter the
  existing metadata intake path.
- Source preflight remains diagnostic only.
- Direct source parsing remains blocked.
- Future source text to Source Intent IR work still requires its own threat
  model evidence, corpus, negative tests, deterministic diagnostics, and
  security review.

## Rejected Alternatives

1. Add `SourceIntentModule.to_compute_graph()`.

   Rejected because direct graph construction would bypass the metadata intake
   review boundary.

2. Add `SourceIntentModule.from_source()`.

   Rejected because source parsing remains blocked.

3. Convert preflight reports into Source Intent IR.

   Rejected because preflight reports are diagnostics, not semantic source
   intent.
