# Runtime Transfer Plan

TUC runtime planning now exposes data movement as concrete plan objects instead
of only aggregate counters.

## Why This Exists

Heterogeneous execution is only useful if the runtime can explain how tensors
move between memory domains and when layout conversion is required. Without an
explicit transfer plan, backend assignment can look correct while hiding the
cost of moving intermediate tensors through the memory hierarchy.

## Current Plan Objects

The first runtime plan objects live in `tuc.runtime.plan`:

- `RuntimeTransferEdge`: a tensor transfer between two backend memory domains.
- `LayoutConversionCost`: a tensor layout conversion required before an
  operation can consume a tensor.

`PartitionPlan` now carries:

- Ordered backend assignments.
- Transfer edges.
- Layout conversion costs.
- Total transfer bytes.
- Total layout conversion bytes.
- Total explicit data movement bytes.

## Security Invariants

Runtime plan objects are declarative data:

- Names are validated.
- Memory domains and layouts are typed enums.
- Transfer and conversion byte counts must be positive and bounded.
- Same-domain transfer edges are rejected.
- No plugin, backend, subprocess, import, or filesystem path is executed while
  constructing a plan.

## Current Limitations

This is still a prototype:

- Transfer cost is byte-count based only.
- Layout conversion cost is byte-count based only.
- Bandwidth, latency, energy, synchronization, buffer lifetime, and overlapping
  transfer/compute are future work.
- Graph input locations are assumed to start in row-major layout unless a
  future frontend/runtime contract states otherwise.

## Next Work

1. Add explicit transfer-edge bandwidth, latency, and energy estimates.
2. Include buffer lifetime and reuse in runtime planning.
3. Emit a stable runtime plan dump.
4. Let backend capability metadata advertise accepted layouts.
5. Add benchmark hooks that compare transfer-aware and transfer-blind plans.
