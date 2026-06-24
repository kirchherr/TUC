# Runtime Layout Conversion Gate Promotion Policy v0

Runtime Layout Conversion Gate Promotion Policy v0 records whether the current
ready layout-conversion evidence may be proposed for Runtime Evidence Gate
enforcement.

The current answer is **promotion ready, not enforced**. This is intentional:
the policy proves that a separate gate-requirement change can be reviewed, but
it does not activate that gate by itself.

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
- Enforcement status: `not_enforced`

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
  `separate_runtime_evidence_gate_requirement_change`.

## What It Means

`promotion_ready: true` means the evidence is ready for a separate maintainer
change that updates Runtime Evidence Matrix requirements and Runtime Evidence
Gate enforcement.

`enforcement_status: not_enforced` means the current report does not change the
gate. Runtime Layout Conversion Evidence remains optional review inventory
until a dedicated gate-enforcement change is accepted.

## Security Boundary

This is a data-only policy report. It does not execute code, inspect devices,
load plugins, allocate memory, run converters, or validate physical residency.

The report must not contain raw tensor values, value digests, runtime handles,
allocation handles, device identifiers, host paths, command lines, generated
code, benchmark samples, plugin entrypoints, or executable artifacts.
