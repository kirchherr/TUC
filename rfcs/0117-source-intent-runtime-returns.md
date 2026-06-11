# RFC 0117: Source Intent Runtime Returns v0

- Status: Accepted
- Related:
  - [Source Intent Return Semantics](../docs/SOURCE_INTENT_RETURN_SEMANTICS.md)
  - [Source Intent Runtime Returns](../docs/SOURCE_INTENT_RUNTIME_RETURNS.md)
  - [Runtime Output Contract](../docs/RUNTIME_OUTPUT_CONTRACT.md)
  - [Runtime Public Output Bundle](../docs/RUNTIME_PUBLIC_OUTPUT_BUNDLE.md)
  - `schemas/source_intent_runtime_returns_report.v0.schema.json`
  - `examples/source_intent_runtime_returns.py`
  - `tests/golden/frontend/source_intent_runtime_returns_report.json`

## Summary

Add Source Intent Runtime Returns v0: a metadata-only evidence bridge proving
that explicit Source Intent public returns can resolve through Runtime Output
Contract and Runtime Public Output Bundle after trusted prototype execution.

## Motivation

Source Intent Return Semantics v0 names public outputs before runtime execution,
but it intentionally does not build runtime artifacts. Runtime Output Contract
and Runtime Public Output Bundle prove public runtime outputs, but they do not
show that the aliases originated from frontend return intent.

TUC needs one reviewed boundary that closes this gap without turning Source
Intent into a parser, a compiler pass, or a runtime executor.

## Design

Source Intent Runtime Returns v0 accepts:

- a validated `SourceIntentModule`
- an already compiled `ComputeGraph`
- an already trusted `RuntimeExecutionResult`

It builds:

- `SourceIntentReturnSemanticsReport`
- a plain alias map from `source_intent_return_aliases(module)`
- Runtime Output Contract evidence
- Runtime Public Output Bundle evidence
- `SourceIntentRuntimeReturnsReport`

The bridge fails closed when:

- the module, graph, and execution graph names do not match
- Source Intent returns are missing
- a return is optional instead of required
- Runtime Output Contract evidence fails
- Runtime Public Output Bundle cannot resolve public values

## Non-Goals

- source parsing
- positional tuple returns
- runtime planning
- kernel execution authorization
- new backend execution surfaces
- raw tensor value serialization
- plugin discovery
- generated artifact loading

## Security

The report is metadata-only. It records contracts, aliases, terminal tensor
names, public output names, digest metadata, and blocked surfaces. It does not
include tensor values, source text, host paths, command lines, device IDs,
generated code, plugin entrypoints, subprocesses, or network locations.

The bridge accepts already constructed in-memory objects and delegates runtime
output validation to the existing Runtime Output Contract and Runtime Public
Output Bundle contracts.

## Acceptance Criteria

- A schema-versioned report contract exists and fails closed.
- A deterministic example proves Source Intent returns resolve to runtime
  public outputs.
- Golden evidence exists without raw tensor values.
- Negative tests cover missing returns, optional returns, mismatched graph
  identity, and failed runtime output contract resolution.
- README, roadmap, and Source Intent docs reference the new boundary.
