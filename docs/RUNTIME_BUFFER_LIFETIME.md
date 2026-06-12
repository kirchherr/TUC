# Runtime Buffer Lifetime

Runtime Buffer Lifetime v0 is a data-only report for conservative produced
tensor lifetimes and exact-match buffer reuse candidates.

Schema:
`schemas/runtime_buffer_lifetime_report.v0.schema.json`

Golden:
`tests/golden/runtime_buffer_lifetime/current_report.json`

Example:

```bash
python examples/runtime_buffer_lifetime.py
```

## What It Records

For every tensor produced by a graph operation, the report records:

- producer operation and operation index
- first live index
- last use index
- last consumer or `graph_output`
- bytes allocated
- memory domain
- produced layout
- dtype and shape
- conservative reuse group

Reuse groups require exact matches for memory domain, layout, dtype, shape, and
byte size. Lifetimes must be non-overlapping with a strict operation-index gap.
This avoids silently treating an operation input and output as reusable during
the same operation.

The report also records `lifetime_metadata_digest`, a deterministic digest over
buffer-lifetime metadata used by Runtime Allocation Plan and Runtime Memory
Planning Gate binding checks.

## Why It Exists

The current runtime planner explains placement, transfers, layout conversion,
and candidate scores. Buffer lifetime evidence is the next practical planning
layer because it makes future memory reuse, buffer pressure, and Von
Neumann-style data movement discussions concrete before adding an allocator.

## Security Boundary

The report is data-only. It consumes an already constructed `ComputeGraph` and
`PartitionPlan`, validates bounded fields, and serializes deterministic JSON.

It does not allocate memory, execute kernels, discover plugins, import backend
modules, load dynamic libraries, spawn subprocesses outside the example
process, access devices, touch the network, execute generated artifacts, run
JIT code, read host paths, read environment variables, load benchmark output,
or authorize executable backend surfaces.

## Current Limitations

- Peak live bytes are conservative across operation boundaries.
- Reuse savings are an upper bound, not an executed allocation result.
- Reuse requires exact shape, dtype, layout, and memory-domain equality.
- In-place operation semantics are not modeled.
- Synchronization, aliasing, buffer pools, and stream overlap remain future
  runtime-planning work.
