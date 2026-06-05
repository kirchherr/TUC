# RFC 0006: Runtime Transfer Plan

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1 to 2

## Summary

TUC adds explicit runtime transfer and layout-conversion plan objects. This
turns data movement from a hidden side effect of backend assignment into an
inspectable runtime planning artifact.

## Motivation

The data-movement-aware IR records read bytes, written bytes, arithmetic
intensity, memory-domain preference, and layout. The next architectural step is
to make runtime consequences explicit:

- Which tensor crosses memory domains?
- Which backend produced it?
- Which backend consumes it?
- How many bytes move?
- Was a layout conversion needed?

This keeps the project aligned with the goal of addressing the memory wall and
the von Neumann bottleneck at compiler and runtime boundaries.

## Decision

Add:

- `RuntimeTransferEdge`
- `LayoutConversionCost`
- `PartitionPlan.transfer_edges`
- `PartitionPlan.layout_conversions`
- `PartitionPlan.total_transfer_bytes()`
- `PartitionPlan.total_layout_conversion_bytes()`
- `PartitionPlan.total_data_movement_bytes()`

The partitioner still uses a small deterministic rule set, but now records
cross-domain transfers and layout conversion costs.

## Security Model

Runtime plans are validated data, not behavior.

- Plan names are bounded simple names.
- Domains and layouts must be known enum values.
- Transfer and conversion byte counts must be positive and bounded.
- Same-domain transfer edges are rejected.
- Plan construction does not execute backend plugin code.

## Consequences

Positive:

- Runtime decisions are more inspectable.
- Future cost models have concrete plan objects to extend.
- Data movement can be tested independently from backend lowering.

Tradeoffs:

- Costs are still byte-count based.
- Bandwidth, latency, energy, synchronization, and buffer lifetime remain future
  work.
- There is not yet a stable runtime-plan dump format.

## Follow-Up Work

1. Add bandwidth, latency, and energy estimates.
2. Add buffer lifetime and reuse.
3. Add backend layout capability metadata.
4. Add runtime plan dumps.
5. Add transfer-aware benchmark comparisons.
