# RFC 0008: Produced Layouts And Transfer Cost Profiles

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1 to 2

## Summary

TUC adds backend-produced layout metadata and validated transfer-cost profiles to
the runtime planning contract. This lets partitioning reason about the layout a
backend emits, not only the layout it can consume, and lets transfer estimates be
calibrated through declarative profile data.

## Motivation

Backend layout support is not symmetric. A backend can accept a blocked input
layout while producing row-major output, vector output, or another backend-local
layout. If TUC assumes accepted layout and produced layout are the same, followup
operations can miss required conversions.

Transfer estimates also need a path from prototype constants toward calibrated
backend data. That path must not introduce executable backend code into
planning, capability checks, or manifest validation.

## Decision

Backend capabilities declare:

- `supported_layouts`: layouts the backend can consume.
- `produced_layouts`: layouts the backend may emit.

Runtime planning records the selected produced layout for each assignment and
uses it as the tensor location for downstream consumers.

Transfer cost modeling adds:

- `TransferCostParameters` for bandwidth, latency, and energy parameters.
- `TransferCostProfile` for source/destination domain-pair estimates.
- `TransferCostProfile.from_manifest(...)` for bounded declarative manifest
  ingestion.
- `DEFAULT_TRANSFER_COST_PROFILE` as the deterministic prototype profile.

`partition_graph(...)` and the compiler pipeline accept an optional validated
transfer-cost profile. When a profile is present, transfer edges and candidate
selection use that profile. When omitted, the existing deterministic default is
used.

## Security Model

Transfer-cost manifests are plain `dict`, `list`, and `tuple` data:

- Profile names are simple validated names.
- Memory domains must map to known typed enum values.
- Numeric cost parameters must be finite and positive where required.
- Duplicate edges, same-domain edges, and oversized edge lists are rejected.
- Manifests do not execute backend code, import modules, spawn subprocesses, or
  read filesystem paths.

Produced layout declarations are validated enum sets. Empty produced-layout sets
are rejected, and layout decisions remain visible in runtime plan dumps.

## Consequences

- Layout conversions caused by backend output layouts are explicit.
- Calibrated transfer costs can be tested without backend plugins or files.
- Runtime plan dumps show produced layout decisions.
- Partitioning can score transfer candidates using latency instead of only byte
  count when profile data is provided.

## Tradeoffs

- Produced-layout selection is intentionally simple and deterministic.
- Profiles are in-memory manifest objects for now; file loading is future work
  and must receive a dedicated threat model.
- Layout conversion cost remains byte-count based until benchmark data exists.

## Follow-Up

1. Add schema-versioned backend manifest files.
2. Add runtime-plan golden dumps.
3. Add buffer lifetime and reuse planning.
4. Add benchmark harnesses comparing default and calibrated profiles.
5. Add fuzz tests once serialized profile parsing exists.
