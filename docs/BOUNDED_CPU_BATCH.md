# Run several datasets with one CPU build

`tuc-cpu-app run-batch` evaluates one supported graph for several named input
sets. Put common weights in `shared_inputs` and changing data in `requests`.
The command builds once and returns all results after execution and cleanup.

Use the installed TUC wheel on Linux x86-64 with the existing local Docker and
private-workspace requirements from the [CPU application guide](BOUNDED_CPU_APPLICATION.md).
The graph can come from the [source converter](BOUNDED_CPU_SOURCE.md) or be
written directly as supported Source Intent JSON.

## Example: one Linear layer, three datasets

Save this as `linear.json`:

```json
{"schema_version":"source_intent.v0","name":"batch_linear",
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

Save this as `batch.json`. Each weight row describes one output feature:

```json
{"schema_version":"tuc.bounded_cpu_batch.v0",
 "shared_inputs":{"weight":[2,-1,1,3],"bias":[0.5,-1]},
 "requests":[
   {"id":"first","inputs":{"x":[2,3]}},
   {"id":"second","inputs":{"x":[-1,2]}},
   {"id":"third","inputs":{"x":[0,0]}}]}
```

```sh
set -e
mkdir -m 700 work
tuc-cpu-app inspect linear.json
tuc-cpu-app run-batch linear.json --batch batch.json --workspace work
```

Expected `results` entries have these IDs and output values:

| ID | `outputs.scores` |
| --- | --- |
| `first` | `[1.5, 10.0]` |
| `second` | `[-3.5, 4.0]` |
| `third` | `[0.5, -1.0]` |

The response also includes a program digest, batch digest and a request digest
for every result. IDs and order bind the batch; changing numerical inputs binds
a different request. Equivalent expanded FP32 inputs retain the same request
digest whether they came from common or individual fields.

## Bounds and errors

There may be 1-16 requests, with unique case-sensitive IDs starting with an
ASCII letter and containing only letters, digits, `_` or `-`, up to 64
characters. `shared_inputs` can be omitted. Every request must supply exactly
the graph inputs not already shared; an overlap rejects instead of overriding.
This applies equally to [gated MLPs](BOUNDED_CPU_GATING.md).
It also supports [row-Softmax classifiers](BOUNDED_CPU_SOFTMAX.md).

The batch JSON limit is 2 MiB. The complete expanded batch has at most 65,536
input values and 65,536 output values; common weights count toward the input
budget for every request. Existing FP32, graph, shape and per-request work
limits remain. All input sets are checked before a build starts.

Malformed batches produce `tuc-cpu-app: batch_json_rejected` and exit code 2.
Execution failures retain the existing closed diagnostics, such as
`numeric_rejection`, and exit code 1. A failure stops the batch, attempts cleanup
of the owned resources and emits no successful result JSON, even when earlier calls
already executed. Successful results appear only after every call and cleanup
have completed. They are not streamed one request at a time.

Common inputs simplify the document. Each request still sends every tensor to
a fresh isolated container. The feature does not retain weights in a running
process, make a performance claim or change the supported graph operations.
For a Python application, the existing [context-managed API](BOUNDED_CPU_APPLICATION.md)
already provides explicit build-once, run-many behavior.

See [RFC 0330](../rfcs/0330-bounded-cpu-batch.md), the
[batch data schema](../schemas/bounded_cpu_batch.v0.schema.json) and the
[independent installed consumer](../integration/bounded_cpu_batch/README.md).

[Installed CI](https://github.com/kirchherr/TUC/actions/runs/35609641378) passed
at `c82d48d`: 642 tests followed by seven batches, 21 ordered results, 96 bitwise
FP32 comparisons, six malformed-input controls and two later numeric rejections.
The [original receipt](evidence/bounded-cpu-batch-35609641378.json) records the
executed source, wheel and consumer. The guide's three example results were
separately calculated; the retained execution receipt covers the consumer corpus.
Final CI and owner review remain required.
