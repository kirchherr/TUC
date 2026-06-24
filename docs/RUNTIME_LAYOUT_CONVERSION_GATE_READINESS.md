# Runtime Layout Conversion Gate Readiness v0

Runtime Layout Conversion Gate Readiness v0 records whether
`runtime_layout_conversion_evidence` is mature enough to become required
Runtime Evidence Gate evidence.

The current answer is **ready**. TUC has two stable layout-conversion evidence
slices, optional Runtime Evidence Matrix inventory, exact Matrix/artifact
binding for the target evidence, and HS-IR/Tensor Store digest binding for the
mixed layout transition.

## Contract

- Schema:
  `schemas/runtime_layout_conversion_gate_readiness_report.v0.schema.json`
- Example: `examples/runtime_layout_conversion_gate_readiness.py`
- Golden:
  `tests/golden/runtime_layout_conversion_gate_readiness/current_report.json`
- RFC: `rfcs/0213-runtime-layout-conversion-gate-readiness.md`
- Digest-binding schema:
  `schemas/runtime_layout_conversion_digest_binding_report.v0.schema.json`
- Digest-binding RFC:
  `rfcs/0214-runtime-layout-conversion-digest-binding.md`
- Contract: `runtime_layout_conversion_gate_readiness.data_only.v0`
- Target graph: `runtime_mixed_backend_equivalence`
- Target artifact kind: `runtime_layout_conversion_evidence`
- Target artifact ID: `runtime_layout_conversion_evidence_mixed`
- Target gate status: `optional_matrix_inventory_not_gate_required`

## Required Checks

The report evaluates:

- `layout_conversion_evidence_report_passes`
- `layout_conversion_schema_and_golden_stable`
- `layout_conversion_negative_tests_present`
- `runtime_evidence_matrix_optional_inventory`
- `second_independent_layout_conversion_slice`
- `gate_exact_artifact_binding`
- `hs_ir_and_tensor_store_digest_binding`

All seven checks currently pass. The final check is satisfied by
`runtime_layout_conversion_digest_binding_mixed`, which binds the source
layout-conversion metadata digest to HS-IR alignment metadata and Tensor Store
record metadata.

## Security Boundary

This is a data-only readiness report. It does not run converters, load backend
plugins, allocate memory, inspect devices, execute generated artifacts, or claim
physical residency.

The report must not contain raw tensor values, value digests, runtime handles,
allocation handles, device identifiers, host paths, command lines, generated
code, benchmark samples, or plugin entrypoints.

## Promotion Rule

Layout Conversion Evidence can now be proposed for Runtime Evidence
Gate-required status, but this document does not activate that gate. Promotion
requires a separate maintainer policy change that updates Runtime Evidence
Matrix requirements and Runtime Evidence Gate enforcement.
