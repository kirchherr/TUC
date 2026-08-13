# Runtime Layout Conversion Gate Promotion Policy v0

Runtime Layout Conversion Gate Promotion Policy v0 records whether the current
ready layout-conversion evidence may be proposed for Runtime Evidence Gate
enforcement.

The current answer is **promotion ready and enforced by Runtime Evidence
Gate**. The policy remains data-only: it records the accepted graph-scoped
promotion decision while the actual enforcement lives in
`examples/runtime_evidence_gate.py`.

## Contract

- Schema:
  `schemas/runtime_layout_conversion_gate_promotion_policy_report.v0.schema.json`
- Example: `examples/runtime_layout_conversion_gate_promotion_policy.py`
- Golden:
  `tests/golden/runtime_layout_conversion_gate_promotion_policy/current_report.json`
- RFC: `rfcs/0215-runtime-layout-conversion-gate-promotion-policy.md`
- Contract:
  `runtime_layout_conversion_gate_promotion_policy.data_only.v0`
- Policy ID: `runtime_layout_conversion_gate_promotion_policy_mixed`
- Promotion scope: `single_graph_candidate`
- Enforcement status: `enforced_by_runtime_evidence_gate`

## What It Records

The report binds the policy decision to:

- target graph `runtime_mixed_backend_equivalence`;
- target artifact kind `runtime_layout_conversion_evidence`;
- target artifact ID `runtime_layout_conversion_evidence_mixed`;
- source Runtime Layout Conversion Gate Readiness contract, schema, readiness
  status, target gate status, and readiness metadata digest;
- source digest-binding artifact ID
  `runtime_layout_conversion_digest_binding_mixed`;
- required next action
  `monitor_runtime_evidence_gate_layout_conversion_requirement`.

## What It Means

`promotion_ready: true` means the evidence has cleared the graph-scoped
promotion prerequisites.

`enforcement_status: enforced_by_runtime_evidence_gate` means Runtime Evidence
Gate now requires `runtime_layout_conversion_evidence_mixed` for
`runtime_mixed_backend_equivalence` and verifies its bindings before the gate
can pass.

## Security Boundary

This is a data-only policy report. It does not execute code, inspect devices,
load plugins, allocate memory, run converters, or validate physical residency.

The report must not contain raw tensor values, value digests, runtime handles,
allocation handles, device identifiers, host paths, command lines, generated
code, benchmark samples, plugin entrypoints, or executable artifacts.
