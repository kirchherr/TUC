# RFC 0116: Source Intent Return Semantics v0

- Status: Accepted
- Date: 2026-06-11
- Related:
  - [Source Intent Return Semantics](../docs/SOURCE_INTENT_RETURN_SEMANTICS.md)
  - [Source Intent JSON Schema](../docs/SOURCE_INTENT_SCHEMA.md)
  - [Source Intent Intake](../docs/SOURCE_INTENT_INTAKE.md)
  - [Runtime Output Contract](../docs/RUNTIME_OUTPUT_CONTRACT.md)
  - [Runtime Public Output Bundle](../docs/RUNTIME_PUBLIC_OUTPUT_BUNDLE.md)
  - `schemas/source_intent.v0.schema.json`
  - `examples/source_intent_return_semantics.py`
  - `tests/golden/frontend/source_intent_return_semantics_report.txt`

## Summary

Add Source Intent Return Semantics v0: explicit, public return names in
`source_intent.v0` plain data, validated as terminal Source Intent tensors and
reported as execution-free metadata.

## Motivation

Runtime Output Contract and Runtime Public Output Bundle now prove that runtime
execution can expose explicit public outputs without leaking tensor values into
review artifacts. The frontend side still needs an equivalent intent boundary:
what did the source-level program mean to return?

Without this layer, public runtime outputs can only be named after compilation,
which leaves a semantic gap between frontend intent and runtime API behavior.

## Decision

Source Intent v0 now accepts optional `returns` entries:

- `public_name`
- `tensor_name`
- `required`

The canonical model adds `SourceIntentReturn`. `SourceIntentModule` validates
that explicit returns:

- reference known tensors
- reference tensors produced by operations
- reference terminal tensors not consumed by later operations
- have unique public names
- have unique returned tensor names

The new report and helper are:

- `build_source_intent_return_semantics_report(module)`
- `dump_source_intent_return_semantics_report(report)`
- `source_intent_return_aliases(module)`

## Non-Goals

- source text parsing
- positional tuple returns
- filesystem or path loading
- metadata conversion authorization
- ComputeGraph construction authorization
- Runtime Output Contract construction
- Runtime Public Output Bundle construction
- tensor value serialization

## Security Boundary

This feature is data-only. It does not execute code, import modules, evaluate
decorators, discover plugins, access devices, load dynamic libraries, spawn
subprocesses, touch the network, or produce generated artifacts.

The return semantics report does not contain source text, tensor values, host
paths, command lines, device identifiers, generated code, plugin entrypoints,
subprocesses, or network locations.

## Acceptance Criteria

- `SourceIntentReturn` exists in the canonical Source Intent model.
- `source_intent.v0` schema documents optional `returns`.
- Runtime intake accepts valid explicit return declarations.
- Runtime intake rejects unknown, input, intermediate, duplicate, and
  execution-surface return declarations.
- A deterministic Source Intent Return Semantics report and golden exist.
- Source Intent metadata conversion preserves return metadata without creating
  runtime evidence.
