# RFC 0058: Source Intent JSON Schema

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC publishes a machine-readable JSON Schema for `source_intent.v0` plain data:

```text
schemas/source_intent.v0.schema.json
```

This RFC does not add source parsing, file loading, preflight-to-intent
conversion, metadata conversion, `ComputeGraph` construction, lowering, runtime
planning, backend selection, plugin discovery, or code execution.

## Motivation

Source Intent Intake now has a schema-versioned runtime contract. External
frontend authors and future parsers need a stable, language-neutral data
contract they can inspect without importing TUC Python code.

## Decision

Add `schemas/source_intent.v0.schema.json` using JSON Schema draft 2020-12.

The schema documents:

- the required top-level fields
- fail-closed `additionalProperties: false` object shapes
- bounded tensor count, operation count, tensor rank, dimensions, and arity
- accepted operation families
- accepted neutral hints

## Security Boundary

The JSON Schema is not the trusted runtime validator. The trusted runtime
boundary remains `source_intent_from_mapping(data)`.

The trusted runtime boundary remains `source_intent_from_mapping(data)`.

The schema must not add file loading, source parsing, Python-object ingestion,
plugin discovery, metadata output, `ComputeGraph` output, lowering, runtime
planning, or backend decisions.

## Evidence

The implementation adds tests that verify:

- schema version matches `SOURCE_INTENT_SCHEMA_VERSION`
- all object shapes fail closed with `additionalProperties: false`
- accepted operation families match runtime intake
- hardware-specific hints such as `prefer_analog_linear` are absent
- source or execution-surface keys such as `python_source`, `file_path`, and
  `plugin_entrypoint` are absent
- the valid Source Intent seed corpus still reaches runtime intake
- docs and RFCs reference `schemas/source_intent.v0.schema.json`

## Consequences

- Source Intent Intake becomes easier for external tools to target.
- Future parser work has a standards-oriented schema artifact to emit.
- Runtime validation remains fail-closed and owned by TUC code.

## Rejected Alternatives

1. Use only Python dataclasses as the public contract.

   Rejected because external frontend authors need a language-neutral artifact.

2. Make JSON Schema validation the only trusted boundary.

   Rejected because TUC must still canonicalize and validate in runtime code
   before constructing Source Intent IR.

3. Add path-based schema loading APIs.

   Rejected because production path handling is outside this slice.
