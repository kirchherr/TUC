# Runtime Layout Conversion Gate Readiness v0

Runtime Layout Conversion Gate Readiness v0 records whether
`runtime_layout_conversion_evidence` is mature enough to become required
Runtime Evidence Gate evidence.

The current answer is intentionally **blocked**. TUC has one stable
layout-conversion evidence slice and optional Runtime Evidence Matrix inventory,
but it does not yet have a second independent slice, exact Runtime Evidence Gate
binding, or HS-IR/Tensor Store digest binding for layout transitions.

## Contract

- Schema:
  `schemas/runtime_layout_conversion_gate_readiness_report.v0.schema.json`
- Example: `examples/runtime_layout_conversion_gate_readiness.py`
- Golden:
  `tests/golden/runtime_layout_conversion_gate_readiness/current_report.json`
- RFC: `rfcs/0213-runtime-layout-conversion-gate-readiness.md`
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

The first four checks currently pass. The final three checks remain blocked by
design.

## Security Boundary

This is a data-only readiness report. It does not run converters, load backend
plugins, allocate memory, inspect devices, execute generated artifacts, or claim
physical residency.

The report must not contain raw tensor values, value digests, runtime handles,
allocation handles, device identifiers, host paths, command lines, generated
code, benchmark samples, or plugin entrypoints.

## Promotion Rule

Layout Conversion Evidence should become Runtime Evidence Gate-required only
after this readiness report is ready and the target evidence has a second
independent proof slice plus exact gate and digest bindings.
