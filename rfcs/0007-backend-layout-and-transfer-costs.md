# RFC 0007: Backend Layout Capabilities And Transfer Costs

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1 to 2

## Summary

TUC adds backend layout capability metadata and deterministic prototype transfer
cost estimates for runtime transfer edges.

## Motivation

The runtime transfer plan shows which tensors move across memory domains. The
next step is to make two additional facts explicit:

- Whether a backend can consume the layout requested by an operation.
- What a transfer approximately costs in latency and energy.

This prepares TUC for transfer-aware and layout-aware backend selection without
executing backend code during capability checks.

## Decision

Backend capabilities now declare:

- `memory_domain`
- `supported_layouts`

Runtime transfer edges now carry a `TransferCostEstimate` containing:

- `bytes_moved`
- `bandwidth_gb_s`
- `base_latency_ns`
- `energy_pj_per_byte`
- derived `estimated_latency_ns`
- derived `estimated_energy_pj`

The prototype uses a small deterministic cost profile keyed by source and
target memory domain. These numbers are intentionally estimates for planning
experiments, not hardware certification claims.

## Security Model

- Backend capabilities remain plain validated data.
- Capability checks do not execute plugin code.
- Unknown layouts fail closed.
- Cost values must be finite and non-negative or positive as appropriate.
- Same-domain transfer estimates are rejected.

## Consequences

Positive:

- Backend selection can reject unsupported layouts.
- Runtime plan dumps can show bandwidth, latency, and energy estimates.
- Future optimizers have a stable schema to extend.

Tradeoffs:

- The current cost profile is coarse.
- Costs do not yet model contention, synchronization, overlap, or buffer reuse.
- Backend layout production is still inferred from operation layout.

## Follow-Up Work

1. Add backend-produced layout metadata separately from operation-requested
   layout.
2. Add calibrated transfer-cost profiles loaded from validated manifests.
3. Model synchronization and buffer lifetimes.
4. Add runtime-plan golden dumps.
5. Add benchmark harnesses that compare cost-model decisions.
