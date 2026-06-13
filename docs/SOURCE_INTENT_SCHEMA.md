# Source Intent JSON Schema

TUC publishes a machine-readable JSON Schema for Source Intent plain data:

```text
schemas/source_intent.v0.schema.json
```

The schema documents the same public contract accepted by
`source_intent_from_mapping(data)`. It is an interoperability artifact for
external frontend authors and future parser work.

## Contract

- Schema version: `source_intent.v0`
- JSON Schema draft: 2020-12
- Runtime intake: `source_intent_intake.execution_free.v0`
- Runtime API: `source_intent_from_mapping(data)`
- Schema file: `schemas/source_intent.v0.schema.json`

The schema defines:

- top-level `name`, `schema_version`, `tensors`, and `operations`
- tensor names, shapes, and dtypes
- operation families: `matmul`, `elementwise`, `reduction`, `softmax`
- symbolic input and output tensor references
- neutral operation attributes: `axis` for `reduction` and `softmax`
- neutral hints: `prefer_linear_accelerator`, `prefer_sparsity`,
  `robust_to_noise`, and `max_error_budget`
- optional public return bindings through `returns`, documented in
  [Source Intent Return Semantics](SOURCE_INTENT_RETURN_SEMANTICS.md)
  and connected to runtime evidence by
  [Source Intent Runtime Returns](SOURCE_INTENT_RUNTIME_RETURNS.md)

All object shapes use `additionalProperties: false`.

## Security Boundary

The JSON Schema is documentation and interoperability guidance. The trusted
runtime boundary remains `source_intent_from_mapping(data)`, which validates and
canonicalizes before constructing `SourceIntentModule`.

The schema does not add:

- source parsing
- file loading
- preflight report ingestion
- Python object inspection
- plugin discovery
- runtime output contract generation
- runtime public output bundle generation
- source-intent runtime returns generation
- metadata output
- `ComputeGraph` output
- lowering or runtime planning

The trusted runtime boundary remains `source_intent_from_mapping(data)`.

## Versioning

Changes to `source_intent.v0` must update:

- `schemas/source_intent.v0.schema.json`
- `SOURCE_INTENT_SCHEMA_VERSION`
- Source Intent Intake tests
- Source Intent Intake docs
- RFC evidence

Incompatible schema changes require a new schema version instead of silently
changing `source_intent.v0`.
