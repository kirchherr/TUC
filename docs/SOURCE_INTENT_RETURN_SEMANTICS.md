# Source Intent Return Semantics

Source Intent Return Semantics v0 defines how frontend-originated compute intent
names public outputs before runtime execution exists.

It is an execution-free data boundary:

```text
source_intent.v0 returns
    -> SourceIntentReturn
    -> SourceIntentReturnSemanticsReport
    -> plain alias map for Runtime Output Contract use
```

## Contract

- Source Intent schema: `schemas/source_intent.v0.schema.json`
- Source Intent contract: `source_intent_ir.canonical.v0`
- Return policy: `explicit_public_returns`
- Return semantics contract: `source_intent_return_semantics.data_only.v0`
- Example: `examples/source_intent_return_semantics.py`
- Golden: `tests/golden/frontend/source_intent_return_semantics_report.txt`
- Runtime bridge:
  [Source Intent Runtime Returns](SOURCE_INTENT_RUNTIME_RETURNS.md)
- Runtime bridge schema:
  `schemas/source_intent_runtime_returns_report.v0.schema.json`

Plain data may now include optional `returns` entries:

```json
{
  "returns": [
    {
      "public_name": "api_y",
      "tensor_name": "y",
      "required": true
    }
  ]
}
```

## What It Proves

The return semantics layer proves that a frontend can declare user-facing output
names without exposing graph-internal naming as the API contract.

For each return:

- `public_name` is the future API-visible output name
- `tensor_name` is the Source Intent tensor being returned
- returned tensors must exist
- returned tensors must be produced by an operation
- returned tensors must be terminal within the Source Intent operation graph
- public names and returned tensor names must be unique

The helper `source_intent_return_aliases(module)` returns a plain
`dict[str, str]` that can later be supplied to Runtime Output Contract evidence
after a graph has been compiled and executed.

The separate [Source Intent Runtime Returns](SOURCE_INTENT_RUNTIME_RETURNS.md)
evidence bridge proves that this alias map resolves through Runtime Output
Contract and Runtime Public Output Bundle after trusted prototype execution.

## Security Boundary

This feature does not parse source text, load files, inspect Python objects,
evaluate decorators, import modules, discover plugins, lower IR, build runtime
plans, execute kernels, or directly build runtime evidence.

The report is metadata-only. It contains public names, tensor names, blocked
surfaces, and contract identifiers. It does not contain tensor values, source
text, host paths, command lines, device identifiers, generated code, plugin
entrypoints, subprocesses, or network locations.

## Current Limitations

- Positional tuple return semantics are out of scope.
- Optional returns are accepted only as explicit public-name bindings.
- Runtime Output Contract and Runtime Public Output Bundle remain separate
  runtime evidence layers, connected only by the explicit runtime returns
  bridge.
- Source text to Source Intent remains blocked by Source-To-Intent Parser Gate.
