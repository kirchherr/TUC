# Canonical Source Intent IR

Canonical Source Intent IR is a data-only frontend boundary between bounded
source syntax data and schema-versioned metadata.

It is not a Triton source parser, not a metadata adapter, not a `ComputeGraph`
constructor, and not a lowering path into TLIR, HAC-IR, HS-IR, runtime plans, or
backend decisions.

It is not a `ComputeGraph` constructor.

## Contract

- Contract: `source_intent_ir.canonical.v0`
- API: `SourceIntentModule`, `SourceIntentOperation`, `SourceIntentTensor`
- Golden: `tests/golden/frontend/source_intent_ir.txt`
- Tests: `tests/test_source_intent_ir.py`

Plain-data construction is handled by
[Source Intent Intake](SOURCE_INTENT_INTAKE.md), not by source parsing.

The v0 contract accepts only:

- bounded tensor names, shapes, and dtypes
- operation families: `matmul`, `elementwise`, `reduction`, `softmax`
- symbolic input and output tensor references
- neutral frontend hints: `prefer_linear_accelerator`, `prefer_sparsity`,
  `robust_to_noise`, and `max_error_budget`
- deterministic dumps for review

## Non-Lowering Boundary

Source Intent IR must not:

- produce metadata
- produce a `ComputeGraph`
- produce TLIR, HAC-IR, or HS-IR
- produce runtime plans or backend decisions
- import user modules
- evaluate decorators
- execute `@triton.jit`
- discover plugins or backends
- read host paths, environment variables, devices, or network resources

The implementation intentionally has no `to_compute_graph` or `to_metadata`
exit. Any future conversion out of Source Intent IR requires a separate RFC,
negative tests, fuzz or property-test corpus, deterministic frontend goldens,
HAC-IR neutrality review, runtime-plan goldens, and compiler decision-report
goldens.

The separate [Source Intent Intake](SOURCE_INTENT_INTAKE.md) adapter may build a
`SourceIntentModule` from schema-versioned plain data. The separate
[Source Intent Metadata Conversion](SOURCE_INTENT_METADATA.md) adapter may
convert an already constructed `SourceIntentModule` into schema-versioned
metadata. Both adapters are separate review boundaries; they are not methods on
Source Intent IR and they do not accept source text or preflight reports.

## Neutrality

Source Intent IR describes what the source appears to intend. It must not name
hardware classes, vendors, memory domains, backend names, plugins, generated
artifacts, host paths, or runtime placement.

Rejected examples include:

- `prefer_analog_linear`
- `tuc.backend`
- `backend`
- `gpu`
- `cuda`
- `device`
- `python_source`
- `file_path`
- `plugin_entrypoint`

Neutral operation intent belongs here. Hardware capability and placement
evidence belong in backend capability data, HS-IR, runtime plans, and compiler
decision reports.

## Relationship To Source Preflight

Triton source preflight remains diagnostic only. It may report bounded syntax
facts and operation-family hints, but it must not create Source Intent IR.

The preflight must not create Source Intent IR.

The accepted future path remains gated:

```text
source text
    ->
bounded syntax data
    ->
canonical source-intent IR
    ->
schema-versioned metadata
    ->
ComputeGraph
```

Only the plain-data to Source Intent IR and Source Intent IR to metadata arrows
exist today. The source-text and preflight arrows around them remain future
work.
