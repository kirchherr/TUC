# Runtime Layout Conversion Gate Readiness v0

Runtime Layout Conversion Gate Readiness v0 records whether
`runtime_layout_conversion_evidence` is mature enough to become required
Runtime Evidence Gate evidence.

The current answer is **ready**. TUC has two stable layout-conversion evidence
slices, Runtime Evidence Matrix required inventory, exact Matrix/artifact
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
- Promotion-policy schema:
  `schemas/runtime_layout_conversion_gate_promotion_policy_report.v0.schema.json`
- Promotion-policy RFC:
  `rfcs/0215-runtime-layout-conversion-gate-promotion-policy.md`
- Contract: `runtime_layout_conversion_gate_readiness.data_only.v0`
- Target graph: `runtime_mixed_backend_equivalence`
- Target artifact kind: `runtime_layout_conversion_evidence`
- Target artifact ID: `runtime_layout_conversion_evidence_mixed`
- Target gate status: `runtime_evidence_gate_required`

## Required Checks

The report evaluates:

- `layout_conversion_evidence_report_passes`
- `layout_conversion_schema_and_golden_stable`
- `layout_conversion_negative_tests_present`
- `runtime_evidence_matrix_required_inventory`
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

Layout Conversion Evidence has been promoted to Runtime Evidence Gate-required
status for `runtime_mixed_backend_equivalence`.

[Runtime Layout Conversion Gate Promotion Policy](RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY.md)
records the current policy state as `promotion_ready: true` and
`enforcement_status: enforced_by_runtime_evidence_gate`.
