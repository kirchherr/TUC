# Reuse a graph with fixed parameters

A model JSON file contains one supported graph and its fixed parameters. Pack
weights once, inspect the remaining inputs, then reuse the model with different
data through single or batch commands. It works with the existing Linear,
calibrated classifier and scaled attention graphs.

Use the installed wheel on Linux x86-64. Executing a model requires the existing
local Docker setup and [private workspace](BOUNDED_CPU_APPLICATION.md).

## Pack a small Linear model

Save `linear.json`:

```json
{"schema_version":"source_intent.v0","name":"reusable_linear",
 "tensors":[{"name":"x","shape":[1,2]},
            {"name":"weight","shape":[2,2]},
            {"name":"bias","shape":[2]},
            {"name":"projected","shape":[1,2]},
            {"name":"y","shape":[1,2]}],
 "operations":[
   {"name":"project","family":"matmul","inputs":["x","weight"],
    "outputs":["projected"],"attributes":{"rhs_transposed":true}},
   {"name":"bias","family":"elementwise","inputs":["projected","bias"],
    "outputs":["y"],"attributes":{"elementwise_kind":"add"}}],
 "returns":[{"public_name":"scores","tensor_name":"y","required":true}]}
```

Save `parameters.json`. Each weight row describes an output feature:

```json
{"schema_version":"tuc.bounded_cpu_inputs.v0",
 "inputs":{"weight":[2,-1,1,3],"bias":[0.5,-1]}}
```

```sh
set -e
tuc-cpu-app pack-model linear.json --parameters parameters.json > model.json
tuc-cpu-app inspect-model model.json
```

Packing prints canonical JSON and runs no model. Inspection reports a model
digest, the compiled program identity, fixed parameter shapes, public outputs
and the remaining input `x`. It does not print parameter values.

Graphs produced by [source conversion](BOUNDED_CPU_SOURCE.md) work the same way.
For a [calibrated classifier](BOUNDED_CPU_SCALING.md), pack `gain`, `offset`,
`weight` and `bias`. For scaled attention, pack `key`, `value` and `scale` when
only the query changes, using the input names declared by your graph.

## Supply only the changing data

Save `inputs.json`:

```json
{"schema_version":"tuc.bounded_cpu_inputs.v0","inputs":{"x":[2,3]}}
```

```sh
mkdir -m 700 work
tuc-cpu-app run-model model.json --inputs inputs.json --workspace work
```

Expected `outputs.scores` is `[1.5,10.0]`. To build once for several inputs,
save `batch.json`:

```json
{"schema_version":"tuc.bounded_cpu_batch.v0","requests":[
  {"id":"first","inputs":{"x":[2,3]}},
  {"id":"second","inputs":{"x":[-1,2]}}]}
```

```sh
tuc-cpu-app run-model-batch model.json --batch batch.json --workspace work
```

The ordered results are `[1.5,10.0]` and `[-3.5,4.0]`. Each result binds its
request digest; the envelope also binds the model, program and complete batch.
Additional shared *variable* inputs use the existing `shared_inputs` field.

## Changing parameters and handling errors

Repack with a new parameter file to create a different model. Parameter changes
change the model digest while the graph's program digest remains the same.
Supplying a fixed parameter through `--inputs` or any batch entry rejects,
even if its values are identical. Model digests detect content differences;
they are not signatures or protection against someone editing the model file.

The model must fix at least one public input and leave at least one variable.
It contains only `schema_version`, `graph` and `parameters`; no external weight
paths, URLs, Python objects, framework checkpoints or executable payloads are
accepted. Packing rounds parameters to FP32 and preserves signed zero. Numeric
values outside the existing checked FP32 domain reject.

Models are limited to 2 MiB. Existing graph limits and the
[batch request and aggregate limits](BOUNDED_CPU_BATCH.md#bounds-and-errors)
still apply after expansion. All batch requests validate before a build begins.
An execution or cleanup error produces no successful result JSON, including
when earlier requests have already executed. Fixed parameters are transmitted
to each isolated run; this does not imply a resident model or a speedup.

Invalid model data or parameter overrides produce `model_json_rejected` with
exit code 2. The existing graph, input and batch diagnostics still apply at
their boundaries. Runtime numeric failures use `numeric_rejection`, exit code 1.

See [RFC 0333](../rfcs/0333-bounded-cpu-model.md) and the
[independent installed client](../integration/bounded_cpu_model/README.md).
The guide values are expected results; installed observations, final CI and
owner review remain required before acceptance.
