# Runtime Materialized Transfer

## Status

Runtime Materialized Transfer v0 is an implemented, opt-in trusted simulator
proof. It materializes the planned `device_sram -> host_ram` edge in the
`systolic-sim -> reference-cpu` graph and binds that execution to the required
layout conversion and passing Runtime Backend Equivalence evidence.

Decision: `rfcs/0296-runtime-materialized-transfer.md`.

## Claim

TUC now proves that one accepted cross-domain runtime plan can drive an actual
owned buffer copy before the consumer executes:

```text
systolic-sim projection
  -> padded 2 x 2 blocked representation
  -> row-major logical buffer
  -> distinct read-only simulator transfer buffer
  -> reference-cpu consumer
  -> terminal output equivalent to the all-reference baseline
```

The copy is real in process. The memory-domain names remain simulator labels;
they are not claims about physical allocation or device residency.

## Opt-In API

```python
execute_graph_with_materialized_data_movement(graph, partition_plan, inputs)
```

This API materializes every supported layout conversion and transfer required
by the plan. `execute_graph()` and
`execute_graph_with_materialized_layouts()` remain unchanged, so accepted
legacy traces retain their existing meaning.

## Complete Preflight

Before input normalization or the first graph kernel, the runtime validates:

- every transfer target is a real consumer input;
- every source is the unique graph producer;
- source and target backends and memory domains match their assignments;
- source and target layouts match the graph and plan;
- every layout-changing transfer has one exact planned conversion;
- planned bytes equal declared tensor shape times graph dtype size;
- transfer edges are unique and within the element limit;
- the domain pair is the fixed `device_sram -> host_ram` v0 pair.

Any incomplete, stale, duplicated, unsupported, or tampered relationship fails
before transfer allocation or kernel execution.

## Execution Semantics

The fixed sequencing policy is `layout_ready_then_domain_copy`:

1. materialize and verify the required `blocked -> row_major` conversion;
2. copy the target-ready logical value into a new contiguous NumPy buffer;
3. verify that source and destination do not share memory;
4. require exact logical equality and finite `float64` values;
5. mark the copied consumer value read-only;
6. execute the trusted consumer kernel.

Planning and runtime bytes remain separate. The current graph declares a
`float32` `(2, 2)` tensor, so the plan records 16 bytes. The trusted prototype
uses `float64`, so the owned runtime copy occupies 32 bytes.

## Evidence

- transfer primitive: `src/tuc/runtime/transfer_executor.py`;
- integrated executor path: `src/tuc/runtime/executor.py`;
- report binding: `src/tuc/runtime/materialized_transfer.py`;
- entry point: `examples/runtime_materialized_transfer.py`;
- schema: `schemas/runtime_materialized_transfer_report.v0.schema.json`;
- golden: `tests/golden/runtime_materialized_transfer/current_report.json`;
- tests: `tests/test_runtime_materialized_transfer.py`.

Run:

```bash
python examples/runtime_materialized_transfer.py
```

The closed report binds the materialized trace, output metadata, materialized
layout report, and Backend Equivalence comparison by SHA-256 metadata digests.
It does not serialize tensor contents or tensor-value digests.

## Security Boundary

The transfer primitive is fixed trusted project code. It does not discover or
load plugins, import backend code, execute generated artifacts, use JIT or
subprocesses, access a device or network, accept paths, expose pointers, create
allocation handles, or consume external artifacts.

The report omits raw tensor values, runtime handles, device identifiers,
memory addresses, paths, commands, source, generated code, and backend
artifacts.

## Non-Claims

This proof does not establish:

- DMA, PCIe, interconnect, or inter-device transfer;
- physical source or target residency;
- runtime allocation handles, streams, events, or synchronization;
- native backend or driver execution;
- measured bandwidth, latency, energy, or performance parity;
- arbitrary domain pairs, layouts, dtypes, or transfer protocols.

The result is the next practical simulator proof: planning now causes both a
real representation change and a real owned data copy while preserving the
same observable computation semantics.
