# RFC 0333: Reusable bounded CPU model data

Status: implemented with observed installed execution; full CI and owner review
remain required.

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

## Observed execution

[CI run 35886433476](https://github.com/kirchherr/TUC/actions/runs/35886433476)
passed at `8e1484a93086f6ab667bcc4863c1e4ec16109ec5`: 758 focused tests, offline
wheel construction and installation outside checkout, then the independent
standard-library client. It observed seven model packs, thirteen single runs
and six two-request batches. All 110 comparisons passed: 38 bitwise Linear
outputs, 72 composed outputs within the stated Softmax tolerances and twelve
visible probability-row checks. A changed-parameter model retained its program
identity and changed its model identity. Eight malformed-data controls and two
arithmetic controls rejected with exact diagnostics, empty stdout, unchanged
fixtures and clean workspaces.

The unchanged [original receipt](../docs/evidence/bounded-cpu-model-35886433476.json)
contains 16,968 bytes with SHA256
`c51c05a6c067cc6df74448525e3601f39a78724275c4a6df1b833fb72be1970c`.
Artifact `10763046799` has ZIP SHA256
`e44c0c5fab174358b88e39dda240e87fe992f3b842f4463fc82b996c5eeb5042`,
matching metadata and the upload log. Wheel SHA256
`c1cb15a94e5dc4f71e214e951d3baa7829cc1e1b58422fe8568935145885f01b`
matches the build log. The consumer hash matches the observed source revision.
The artifact retains the receipt, not the wheel or native images.

A separate local audit reconstructed six canonical models and their program
identities, the changed parameter model, 28 request bindings, seven batch
digests, all eight negative classifications and both numeric-control identities.
Independent NumPy equations matched all 110 observed values, including 38 exact
FP32 bit patterns. Maximum absolute composed-output difference was
`5.960464477539063e-08`; maximum row-mass difference was
`8.195638656616211e-08`. The audit did not repeat native execution.

The existing Scaling audit also reconstructed its six retained programs and
unchanged native context and observations. This extension changes host data
packaging and CLI dispatch; it adds no native arithmetic. Full CI and owner
review remain separate from these fixed-corpus observations.
