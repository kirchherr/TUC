# Runtime Materialized Layout Conversion

## Status

Runtime Materialized Layout Conversion v0 is an implemented, opt-in trusted
simulator proof. It materializes one bounded `blocked -> row_major` conversion
for the mixed `systolic-sim -> vector-sim` graph and binds that execution to
passing Runtime Backend Equivalence evidence.

Decision: `rfcs/0295-runtime-materialized-layout-conversion.md`.

## Claim

TUC now proves that its accepted runtime plan can drive an actual in-process
buffer representation change before a downstream trusted simulator consumes a
value:

```text
logical projection value
  -> padded 2 x 2 tiled blocked buffer
  -> row-major logical buffer
  -> vector-sim consumer
  -> terminal output equivalent to reference-cpu
```

The converter verifies the reconstructed logical values exactly before the
consumer operation runs. The resulting report contains metadata only. It binds
the materialized trace digest and candidate output-manifest digest to the exact
candidate run metadata accepted by Runtime Backend Equivalence.

## Opt-In Boundary

The existing `execute_graph()` API remains the compatibility path. Its legacy
layout evidence and trace index continue to state
`conversion_not_materialized_as_runtime_step`.

The new API is explicit:

```python
execute_graph_with_materialized_layouts(graph, partition_plan, inputs)
```

This avoids silently changing old traces, goldens, receipts, or evidence-gate
meaning. Promotion into the default executor or the general Runtime Evidence
Gate requires a separate decision.

## Fixed Converter

The v0 converter accepts exactly:

- source layout `blocked`;
- target layout `row_major`;
- positive rank-2 tensors;
- a fixed `2 x 2` tile;
- finite internal NumPy `float64` values;
- a `LayoutConversionCost` whose planned byte count matches the graph tensor
  dtype and shape;
- an internal producer and a declared consumer input.

The complete conversion plan is checked before input normalization or kernel
execution. Unknown operations, incorrect producer linkage, unsupported layouts,
stale byte counts, duplicate conversions, shape drift, dtype drift, and
non-finite values fail closed.

## Representation Accounting

The proof deliberately distinguishes planning bytes from simulator bytes. For
the current `(2, 3)` projection:

| Fact | Value |
| --- | ---: |
| Planned graph dtype | `float32` |
| Planned conversion bytes | 24 |
| Trusted runtime dtype | `float64` |
| Logical runtime bytes | 48 |
| Physical blocked shape | `(1, 2, 2, 2)` |
| Physical blocked bytes | 64 |
| Padding elements | 2 |
| Temporary conversion storage | 112 bytes |

This makes the prototype's intentional runtime dtype widening visible instead
of conflating it with the graph-level movement estimate.

## Evidence

- implementation: `src/tuc/runtime/layout_conversion_executor.py`;
- report binding: `src/tuc/runtime/materialized_layout_conversion.py`;
- proof entry point: `examples/runtime_materialized_layout_conversion.py`;
- schema: `schemas/runtime_materialized_layout_conversion_report.v0.schema.json`;
- golden: `tests/golden/runtime_materialized_layout_conversion/current_report.json`;
- tests: `tests/test_runtime_materialized_layout_conversion.py`.

Run:

```bash
python examples/runtime_materialized_layout_conversion.py
```

## Security Boundary

The converter is fixed trusted project code. It does not discover plugins,
import backend modules, load dynamic libraries, execute generated artifacts,
spawn subprocesses, access devices, use the network, or consume external
artifacts. Converted arrays are read-only before reaching the consumer.

The public report omits tensor values, tensor digests, runtime handles, device
identifiers, paths, commands, source, generated code, and backend artifacts.

## Non-Claims

This proof does not establish:

- native backend execution;
- physical device residency;
- a device-produced blocked buffer;
- DMA or inter-device transfer;
- native layout ABI compatibility;
- zero-copy conversion;
- performance parity or timing;
- arbitrary ranks, tiles, dtypes, or layout pairs.

The trusted runtime still keeps canonical logical NumPy values in its internal
tensor store. At the conversion boundary, v0 reconstructs the planned blocked
simulator representation and converts it back to row-major form. That is a real
bounded buffer transformation, but it is not evidence about physical hardware.

[Runtime Materialized Transfer](RUNTIME_MATERIALIZED_TRANSFER.md) builds on this
opt-in path by copying the target-ready value into a distinct simulator buffer
for a cross-domain consumer while preserving the same non-native claim boundary.
