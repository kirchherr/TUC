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
- `TransferCostEstimate`: deterministic prototype bandwidth, latency, and
  energy estimate for a transfer edge.
- `TransferCostProfile`: validated per-domain transfer parameters that can be
  loaded from plain manifest data before runtime planning.

`PartitionPlan` now carries:

- Ordered backend assignments.
- Transfer edges.
- Layout conversion costs.
- Total transfer bytes.
- Total layout conversion bytes.
- Total explicit data movement bytes.
- Estimated total transfer latency.
- Estimated total transfer energy.

## Golden Dumps

Runtime plan text dumps are covered by golden fixtures in
`tests/golden/runtime_plans/`. The current fixtures cover default transfer
costing, backend-produced layout conversion, and calibrated transfer-cost
profiles.

Fixture updates are intentional compiler-contract changes. They should stay
small, readable, and tied to typed in-memory graph construction rather than
external generators.

Compiler decision reports complement runtime-plan dumps by showing which
registered backend capabilities accepted or rejected each operation before the
runtime assignment was finalized.

## Security Invariants

Runtime plan objects are declarative data:

- Names are validated.
- Memory domains and layouts are typed enums.
- Transfer and conversion byte counts must be positive and bounded.
- Transfer cost numbers must be finite and validated.
- Transfer-cost manifests are accepted only as bounded plain `dict`, `list`, and
  `tuple` data.
- Transfer-cost profile files must pass the schema-versioned JSON loader before
  becoming runtime profile data.
- Same-domain transfer edges are rejected.
- No plugin, backend, subprocess, import, or filesystem path is executed while
  constructing a plan or validating a transfer profile.

## Current Limitations

This is still a prototype:

- Transfer cost uses a coarse deterministic prototype profile.
- Optional calibrated profiles can be loaded from schema-versioned JSON files.
- Layout conversion cost is byte-count based only.
- Synchronization, buffer lifetime, contention, calibration, and overlapping
  transfer/compute are future work.
- Graph input locations are assumed to start in row-major layout unless a
  future frontend/runtime contract states otherwise.

## Next Work

1. Include buffer lifetime and reuse in runtime planning.
2. Add benchmark hooks that compare transfer-aware and transfer-blind plans.
