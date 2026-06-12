# Source-To-Intent Research Execution Bridge

Source-To-Intent Research Execution Bridge v0 proves that accepted explicit
research parser output can be re-entered as `source_intent.v0` plain data and
executed through the normal TUC runtime evidence path.

It does not open the default source parser path and does not let source text
produce compiler artifacts directly.

## Contract

- Bridge contract: `source_to_intent_research_execution_bridge.explicit.v0`
- Report schema version:
  `tuc.source_to_intent_research_execution_bridge_report.v0`
- Report schema:
  `schemas/source_to_intent_research_execution_bridge_report.v0.schema.json`
- Example: `examples/source_to_intent_research_execution_bridge.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_execution_bridge.json`
- Tests: `tests/test_source_to_intent_research_execution_bridge.py`
- CI entry: `.github/workflows/ci.yml`

## What It Proves

For each accepted research parser slice, the bridge runs:

```text
Research parser result
    ->
source_intent.v0 plain data re-intake
    ->
SourceIntentModule
    ->
Source Intent Metadata Conversion
    ->
ComputeGraph
    ->
HAC-IR and Runtime Plan
    ->
Runtime Execution Readiness
    ->
Runtime Executor
    ->
Runtime Reference Correctness
```

The current accepted cases are:

- `research_matmul_elementwise`
- `research_softmax_reduction`

The report records only metadata and digests:

- plain-data digest
- parser report digest
- metadata report digest
- metadata intake digest
- HAC-IR digest
- runtime-plan digest
- compiler-decision digest
- readiness digest
- execution-trace digest
- reference-correctness digest
- comparison metadata digest

Raw source text, raw Source Intent payloads, raw tensor values, runtime tensor
values, generated code, backend artifacts, host paths, environment variables,
device handles, and subprocess output are omitted.

## Security Boundary

The bridge consumes accepted in-memory research parser results and explicitly
re-enters through `source_intent_from_mapping(...)`. It does not read source
files by path, import user modules, evaluate decorators, execute `@triton.jit`,
discover plugins, access devices, run subprocesses, load dynamic libraries, or
execute generated artifacts.

Parser output remains `source_intent.v0` plain data only. Metadata,
`ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime-plan, and backend-decision outputs
remain blocked at the parser boundary; they are produced only after the
separate Source Intent Intake and Metadata Conversion path accepts the plain
data.

## Review Meaning

This bridge is the practical runtime counterpart to the research parser
conformance and diagnostics evidence. It shows that the accepted source-to-
intent research slices are not only parseable and conformant, but can also
reach controlled execution through the same audited runtime path used by the
rest of TUC.

The Source-To-Intent Research Evidence Gate binds this bridge by digest.
