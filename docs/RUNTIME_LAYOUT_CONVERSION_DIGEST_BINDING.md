# Runtime Layout Conversion Digest Binding v0

Runtime Layout Conversion Digest Binding v0 connects three existing data-only
runtime artifacts for the mixed backend-equivalence proof slice:

- Runtime Layout Conversion Evidence;
- Runtime HS-IR Plan Alignment;
- Runtime Tensor Store Evidence.

It proves that the planned `blocked -> row_major` layout transition is bound to
the same graph, compatible HS-IR layout decisions, and Tensor Store value-record
metadata. It does not run a converter.

## Contract

- Schema:
  `schemas/runtime_layout_conversion_digest_binding_report.v0.schema.json`
- Example: `examples/runtime_layout_conversion_digest_binding.py`
- Golden:
  `tests/golden/runtime_layout_conversion_digest_binding/current_report.json`
- RFC: `rfcs/0214-runtime-layout-conversion-digest-binding.md`
- Contract: `runtime_layout_conversion_digest_binding.data_only.v0`
- Artifact ID: `runtime_layout_conversion_digest_binding_mixed`
- Scope: `metadata_digest_and_record_id_binding`

## What It Binds

The report records only bounded metadata:

- source layout-conversion contract, schema, pass status, counts, and digests;
- source HS-IR alignment contract, schema, pass status, counts, and digest;
- source Tensor Store Evidence contract, schema, pass status, counts, and
  record-metadata digest;
- one row per planned conversion with operation IDs, record IDs, layouts,
  memory domains, backends, byte counts, and binding status.

For the current mixed slice, the binding row checks that `projection` is
produced by `systolic-sim` in `blocked` layout and consumed by `normalize` on
`vector-sim` in `row_major` layout, with 24 planned conversion bytes.

## Security Boundary

This report is data-only. It must not contain raw tensor values, tensor-value
digests, runtime handles, allocation handles, device identifiers, host paths,
command lines, generated code, benchmark samples, plugin entrypoints, or
executable artifacts.

Failures are reported as derived issues. A graph mismatch, failed source
report, mismatched layout, mismatched backend, mismatched memory domain,
mismatched producer ID, or mismatched byte count blocks the binding.

## Relationship To Gate Readiness

Runtime Layout Conversion Gate Readiness uses this report to satisfy
`hs_ir_and_tensor_store_digest_binding`.

A ready readiness report still does not make layout-conversion evidence a
Runtime Evidence Gate requirement by itself. Promotion remains a separate
maintainer policy change.
