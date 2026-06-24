# RFC 0213: Runtime Layout Conversion Gate Readiness

## Status

Accepted

## Summary

Add a data-only readiness report for deciding when
Runtime Layout Conversion Evidence can become required Runtime Evidence Gate
evidence.

This RFC does not make layout conversion evidence gate-required. It records the
promotion prerequisites and now points to the digest-binding evidence that makes
the current readiness report ready.

## Motivation

Runtime Layout Conversion Evidence now makes planned layout transitions visible
and inventories the first mixed backend-equivalence report in the Runtime
Evidence Matrix. That is useful, but it is not yet enough to promote the
artifact into a merge gate.

Without an explicit readiness report, TUC could accidentally turn narrow proof
slices into a general gate requirement before digest bindings exist. That would
weaken the Universal Compute proof by making review evidence look more
operationally bound than it is.

## Goals

- State the exact prerequisites for making layout-conversion evidence
  gate-required.
- Keep the current artifact optional until those prerequisites are met.
- Bind readiness to the current layout-conversion evidence metadata without
  exposing values, handles, devices, paths, or executable surfaces.
- Preserve the distinction between optional Runtime Evidence Matrix inventory
  and required Runtime Evidence Gate evidence.

## Non-Goals

- Implement a runtime layout converter.
- Add native device execution.
- Prove physical memory residency.
- Add allocation handles, memory addresses, streams, kernels, or memory pools.
- Make `runtime_layout_conversion_evidence` a Runtime Evidence Gate
  requirement.
- Add source parser or backend plugin execution paths.

## Proposal

Introduce `RuntimeLayoutConversionGateReadinessReport` with schema
`schemas/runtime_layout_conversion_gate_readiness_report.v0.schema.json`.

Runtime Layout Conversion Digest Binding is defined in
`schemas/runtime_layout_conversion_digest_binding_report.v0.schema.json` and
RFC 0214.

The report records:

- the source layout-conversion evidence contract and schema version;
- source graph name, conversion count, metadata digest, and partition-plan
  digest;
- required readiness checks;
- derived readiness issues;
- target graph, artifact kind, artifact ID, and current gate status;
- blocked execution surfaces.

The current report is ready because RFC 0214 adds HS-IR and Runtime Tensor
Store digest binding for the mixed layout transition.

## Invariants

- Check order is fixed and schema-versioned.
- Issues must be derived from non-passing checks.
- A source report with layout-conversion issues cannot be marked as passed.
- A source report with zero conversion records cannot satisfy the source
  evidence check.
- The report remains data-only and execution-free.

## Compatibility

This is additive. It does not change Runtime Evidence Matrix completeness,
Runtime Evidence Gate behavior, or layout-conversion evidence generation.

## Testing

The v0 implementation adds:

- a deterministic readiness example and golden report;
- a second independent layout-conversion evidence example and golden report;
- a digest-binding example and golden report;
- schema checks for constants, check order, and fail-closed objects;
- negative tests for forged issues, wrong check order, wrong Matrix artifact
  binding, and forbidden execution surface text;
- documentation references from the layout-conversion evidence docs and roadmap.

## Open Questions

- Should layout-conversion evidence be promoted as a required gate only for the
  mixed backend-equivalence graph first, or should TUC define a broader
  per-graph promotion policy?
- Should no-op layout preservation records ever count toward readiness?
