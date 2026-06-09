# RFC 0055: Source Intent Intake

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC adds a schema-versioned plain-data intake path for canonical Source Intent
IR.

This RFC does not add source parsing, preflight-to-intent conversion,
filesystem loading, Python-object ingestion, metadata conversion,
`ComputeGraph` construction, TLIR lowering, HAC-IR lowering, runtime planning,
backend selection, plugin discovery, or code execution.

The new contracts are:

```text
source_intent.v0
source_intent_intake.execution_free.v0
```

## Motivation

RFC 0053 created the Source Intent IR data model. RFC 0054 proved that an
already constructed `SourceIntentModule` can enter the metadata path through a
separate adapter. The next controlled step is a data-only intake schema that
external frontends and future parsers can target without opening a source-code
execution surface.

## Decision

Add `tuc.frontend.source_intent_intake` with:

- `SOURCE_INTENT_SCHEMA_VERSION`
- `SOURCE_INTENT_INTAKE_CONTRACT`
- `SourceIntentIntakeReport`
- `source_intent_from_mapping`
- `build_source_intent_intake_report`

The intake accepts only plain `dict`, `list`, and `tuple` data. Unsupported
fields fail closed.

## Accepted Scope

The intake may:

- accept an already decoded plain mapping
- validate schema version
- build `SourceIntentTensor`, `SourceIntentOperation`, and `SourceIntentModule`
- emit deterministic intake evidence
- hand the resulting module to the separate Source Intent Metadata Conversion
  adapter

## Rejected Scope

The intake must not:

- parse source text
- consume preflight reports
- load files or paths
- import user modules
- inspect Python function objects
- evaluate decorators
- execute `@triton.jit`
- discover plugins or backends
- access devices, environment variables, network resources, or subprocesses
- produce metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, or
  backend decisions directly

## Evidence

The implementation adds:

- schema-versioned intake unit tests
- negative tests for source text, unsupported schema versions, unknown keys,
  and execution-surface data
- deterministic intake report golden
- deterministic Source Intent module golden from plain data
- deterministic metadata intake golden after the separate conversion adapter
- documentation in `docs/SOURCE_INTENT_INTAKE.md`
- example in `examples/source_intent_intake.py`

## Consequences

- External tools can target a stable Source Intent data shape without modifying
  TUC core.
- Future parser work has a contract to emit, but no source parser exists yet.
- Source text and preflight reports remain blocked from Source Intent IR.

## Rejected Alternatives

1. Add path-based loading helpers.

   Rejected because path handling should be designed separately with traversal,
   sandboxing, and artifact-size controls.

2. Accept source strings in the intake function.

   Rejected because source parsing remains blocked.

3. Convert intake data directly to metadata.

   Rejected because the `SourceIntentModule` validation boundary must remain
   visible before metadata conversion.
