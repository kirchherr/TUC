# RFC 0214: Runtime Layout Conversion Digest Binding

## Status

Accepted

## Summary

Add a data-only report that binds Runtime Layout Conversion Evidence to
Runtime HS-IR Plan Alignment and Runtime Tensor Store Evidence for the mixed
backend-equivalence proof slice.

This closes the final `hs_ir_and_tensor_store_digest_binding` prerequisite in
Runtime Layout Conversion Gate Readiness without executing a layout converter
or making layout-conversion evidence gate-required.

## Motivation

Runtime Layout Conversion Evidence makes planned layout transitions visible,
but visibility alone is not enough for promotion readiness. The transition must
also be tied to the backend/layout decisions in HS-IR and to the Runtime Tensor
Store value-record metadata that names the producer, backend, memory domain,
and logical layout.

Without this binding, a stale or mismatched layout-conversion report could look
complete while referring to different HS-IR or Tensor Store evidence.

## Goals

- Bind layout-conversion metadata digest, HS-IR alignment metadata digest, and
  Tensor Store record metadata digest in one review artifact.
- Record one bounded row per planned conversion.
- Fail closed on graph mismatches, failed source reports, layout mismatches,
  backend mismatches, memory-domain mismatches, producer mismatches, and byte
  count mismatches.
- Keep the artifact data-only and free of tensor values, handles, device IDs,
  paths, generated artifacts, plugin entrypoints, and executable surfaces.
- Satisfy the final Runtime Layout Conversion Gate Readiness prerequisite.

## Non-Goals

- Implement runtime layout conversion.
- Execute native code, generated artifacts, backend plugins, kernels, streams,
  or device APIs.
- Prove physical memory residency.
- Add allocation handles, memory addresses, device pointers, or memory pools.
- Make Runtime Layout Conversion Evidence a Runtime Evidence Gate requirement.
- Claim native performance or vendor-library parity.

## Proposal

Introduce `RuntimeLayoutConversionDigestBindingReport` with schema
`schemas/runtime_layout_conversion_digest_binding_report.v0.schema.json`.

The report records:

- graph name;
- source layout-conversion contract, schema version, pass status, issue count,
  conversion count, planned bytes, metadata digest, and partition-plan digest;
- source HS-IR alignment contract, schema version, pass status, issue count,
  step count, layout-conversion count, layout-conversion bytes, and metadata
  digest;
- source Tensor Store Evidence contract, schema version, pass status, issue
  count, record count, and record-metadata digest;
- binding rows for each conversion;
- derived issues;
- blocked execution surfaces and raw-value omission policy.

The current artifact ID is `runtime_layout_conversion_digest_binding_mixed`.

## Invariants

- Issues must be derived from report fields and binding rows.
- A failed source report blocks the binding.
- Source graph names must match.
- Layout conversion counts and planned bytes must match HS-IR alignment counts
  and bytes.
- Each binding row must agree on source backend, target backend, source layout,
  target layout, source memory domain, source producer ID, and planned bytes.
- Binding rows must not expose raw tensor values or raw value digests.

## Compatibility

This is additive. It updates Runtime Layout Conversion Gate Readiness from
blocked to ready, but it does not change Runtime Evidence Matrix required
artifact kinds or Runtime Evidence Gate enforcement.

## Testing

The v0 implementation adds:

- a deterministic example and golden report;
- schema checks for constants, status enums, fail-closed objects, and forbidden
  fields;
- negative tests for graph mismatch, Tensor Store layout mismatch, forged
  issues, and forbidden execution surface text;
- Readiness coverage for a forged digest-binding digest.

## Open Questions

- Should the next promotion step make layout-conversion evidence required only
  for `runtime_mixed_backend_equivalence`, or define a broader per-graph
  requirement policy first?
- Should no-op layout preservation records get a separate binding artifact, or
  remain out of scope until real converter behavior exists?
