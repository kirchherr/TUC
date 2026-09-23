# RFC 0333: Reusable bounded CPU model data

Status: implementation in progress; observed installed execution, final CI and
owner review required.

## Decision and value

Bundle an existing bounded Source Intent graph with fixed named FP32 parameters
in one data-only JSON document. A calibrated classifier can carry its gain,
offset, weights and bias; a scaled attention graph can carry keys, values and
scale. Callers supply only changing inputs. This separates a reusable computation
and parameter identity from individual requests without adding model-framework
imports, executable serialization or backend details to HAC-IR.

The versioned `tuc.bounded_cpu_model.v0` envelope has exactly `schema_version`,
`graph` and `parameters`. Graph syntax, operations and resource budgets are
unchanged. Parameters must cover a nonempty proper subset of public graph inputs.
At least one input remains variable. Parameters are finite normal-or-signed-zero
FP32 arrays with exactly the declared lengths. Canonical output rounds parameters
to FP32, preserves signed zero, fills existing graph defaults and sorts object
keys. Tensor/operation/return array order remains significant.

The model digest binds the canonical graph and parameter FP32 bit patterns. It
is independent of the selected CPU program digest. Changing a fixed parameter
changes the model identity while leaving the graph program identity unchanged.
Expanded requests retain the existing request and batch digests. Digests are
consistency identities, not signatures or authorization to execute.

## Public commands

- `tuc-cpu-app pack-model GRAPH.json --parameters INPUTS.json` validates data and
  prints canonical model JSON. It creates no files, processes or native code.
- `tuc-cpu-app inspect-model MODEL.json` reports model/program identities, fixed
  parameter bindings, remaining variable inputs and public outputs, without
  exposing parameter values or executing the model.
- `tuc-cpu-app run-model MODEL.json --inputs INPUTS.json --workspace DIR` merges
  fixed parameters with exact remaining inputs and uses the existing CPU runner.
- `tuc-cpu-app run-model-batch MODEL.json --batch BATCH.json --workspace DIR`
  permits additional shared variable inputs and 1-16 requests. No request or
  shared input may override a model parameter, even with an identical value.

New model result envelopes carry model, program and request/batch identities.
Existing graph commands, schemas, generated artifacts and numerical behavior
remain unchanged. All batch inputs validate before runtime import/build; results
publish only after all requests and cleanup succeed. Weights are not retained
inside a resident native process and no speedup is claimed.

## Security boundary

The new input is bounded JSON, not an archive, path manifest, pickle, Python
module or framework checkpoint. Unknown fields, duplicate keys, malformed UTF-8,
lone surrogates, excessive nesting/tokens, unbounded number spellings, nonfinite
values, overflow/subnormal/rounded-zero values, incorrect bindings and overrides
reject with closed diagnostics. Existing no-follow regular-file reads apply.
There are no referenced files, download URLs, imports or plugin hooks.

Model JSON is at most 2 MiB, depth 13 and 204,096 lexical tokens. Embedded graph
JSON still passes the original 64 KiB/depth/token limits. Parameters use at most
24 bindings, 4,096 values per tensor and 65,536 values total. To preserve integer
graph dimensions and signed-zero parameter literals, the bounded JSON decoder
reads the same bytes in graph and numeric modes; both passes have fixed limits.
Expanded batches retain the original byte, input, output and request budgets.

Validation includes canonical round trips, identity changes, equality of expanded
request/batch identities with existing commands, hostile inputs and objects,
overrides in the last request, failure-before-build and no partial output on
runtime/cleanup errors. An independent installed client must pack and execute
legacy Linear, calibrated classifier and scaled attention models with multiple
profiles, compare results with separate FP32 equations, and observe rejection
and cleanup behavior. Unit tests and candidate reports are not native evidence.
