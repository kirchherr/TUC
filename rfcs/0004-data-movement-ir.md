# RFC 0004: Data Movement Aware IR

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1 to 2

## Summary

TUC must model data movement explicitly in HAC-IR and carry those facts into
HS-IR. This prepares the compiler for the memory wall and the von Neumann
bottleneck as accelerators become faster and more heterogeneous.

## Motivation

Accelerator arithmetic throughput can improve faster than host memory,
interconnects, layout conversion, synchronization, and device-local buffer
management. If TUC only models compute operations, it may make backend choices
that look optimal in isolation but are poor once transfers are included.

Data movement must therefore be visible before backend specialization and
runtime scheduling.

## Decision

The prototype adds:

- `MemoryDomainKind`
- `MemoryDomain`
- `TransferEdge`
- `LayoutConstraint`
- `MovementEstimate`
- A compiler movement pass that annotates HAC-IR operations.
- An HS-IR `movement_summary` metadata entry.

For the MVP, movement estimates cover:

- MatMul
- Elementwise
- Reduction
- Softmax

The estimates are deliberately conservative and deterministic. They are not a
global optimizer yet.

## Security Model

Movement data is treated as untrusted until produced by the compiler pass.

Rules:

- Reject unknown dtypes.
- Reject invalid shape relationships.
- Enforce estimator resource limits.
- Overwrite user-supplied movement attributes.
- Fail closed if movement summaries are requested from unannotated graphs.
- Do not execute backend plugin code during capability or movement checks.

This prevents movement metadata from becoming a code-execution or
resource-exhaustion surface.

## Consequences

Positive:

- HAC-IR now contains the first explicit memory-wall signal.
- HS-IR can explain backend decisions with compute and movement context.
- Future partitioning can compare compute speed against transfer cost.
- The IR can evolve toward hardware with local SRAM, analog arrays,
  neuromorphic memory fabrics, or persistent memory.

Tradeoffs:

- Estimates are approximate.
- MatMul is rank-2 only in the prototype.
- Broadcasting and complex layout conversions are intentionally deferred.
- Backend memory domains are not yet negotiated through the capability schema.

## Follow-Up Work

1. Add backend memory-domain capability schema.
2. Model transfer edges between backend assignments.
3. Extend partitioning to penalize excessive transfers.
4. Add layout conversion and buffer lifetime tracking.
5. Add fuzzing around serialized movement metadata once external IR input
   formats exist.
