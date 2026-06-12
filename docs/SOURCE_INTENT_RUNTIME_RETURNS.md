# Source Intent Runtime Returns

Source Intent Runtime Returns v0 proves the first practical return path from
frontend-declared public outputs to runtime public outputs.

It is a narrow evidence bridge:

```text
source_intent.v0 returns
    -> SourceIntentReturnSemanticsReport
    -> Source Intent metadata conversion
    -> compiled ComputeGraph
    -> trusted Runtime Executor result
    -> Runtime Output Contract
    -> Runtime Public Output Bundle
    -> SourceIntentRuntimeReturnsReport
```

## Contract

- Report schema: `schemas/source_intent_runtime_returns_report.v0.schema.json`
- Report schema version: `tuc.source_intent_runtime_returns_report.v0`
- Runtime returns contract: `source_intent_runtime_returns.evidence.v0`
- Source Intent contract: `source_intent_ir.canonical.v0`
- Return semantics contract: `source_intent_return_semantics.data_only.v0`
- Output contract: `runtime_output_contract.data_only.v0`
- Public output bundle contract: `runtime_public_output_bundle.readonly_values.v0`
- Example: `examples/source_intent_runtime_returns.py`
- Golden: `tests/golden/frontend/source_intent_runtime_returns_report.json`

## What It Proves

The report proves that explicit Source Intent returns can be resolved through
the runtime's existing public output boundary:

- Source Intent public names are preserved as Runtime Output Contract aliases.
- Source Intent return tensors must match terminal runtime graph outputs.
- Runtime Output Contract must pass before public values are resolved.
- Runtime Public Output Bundle must build read-only public values.
- Review evidence stays metadata-only and omits tensor values.

## Security Boundary

This bridge does not parse source text, import Python modules, evaluate
decorators, discover backend plugins, lower IR, plan runtime placement, execute
kernels, load generated artifacts, or serialize tensor values.

It accepts only already constructed objects from reviewed boundaries:

- `SourceIntentModule`
- `ComputeGraph`
- `RuntimeExecutionResult`

The bridge fails closed if the Source Intent module name, runtime graph name,
or execution trace graph name diverge. It also fails closed if Runtime Output
Contract evidence does not pass.

## Current Limitations

- Only required named returns are accepted in v0.
- Positional tuple returns remain out of scope.
- Source text to Source Intent remains blocked by Source-To-Intent Parser Gate.
- The example uses trusted in-process prototype runtime execution only.
