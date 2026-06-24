# RFC 0215: Runtime Layout Conversion Gate Promotion Policy

## Status

Accepted

## Summary

Add a data-only promotion policy report for deciding whether the ready Runtime
Layout Conversion Evidence can be proposed as Runtime Evidence Gate-required
evidence.

This RFC does not activate the gate. It records that the current evidence is
ready for a separate gate-enforcement change.

## Motivation

Runtime Layout Conversion Gate Readiness is now ready, and Runtime Layout
Conversion Digest Binding connects the planned layout transition to HS-IR and
Runtime Tensor Store evidence. The next risk is procedural: accidentally
treating "ready" as "already enforced".

TUC needs a small policy artifact between readiness and enforcement so reviewers
can distinguish:

- evidence maturity;
- policy scope;
- actual Runtime Evidence Gate activation.

## Goals

- Record the exact graph-scoped promotion candidate.
- Keep promotion scope limited to the current mixed backend-equivalence graph.
- Bind the policy to the readiness metadata digest.
- Require the expected digest-binding artifact ID.
- State that enforcement remains disabled until a separate gate-requirement
  change is accepted.
- Keep the artifact data-only and free of execution surfaces.

## Non-Goals

- Modify Runtime Evidence Matrix required artifact kinds.
- Modify Runtime Evidence Gate enforcement.
- Execute layout converters, generated code, backend plugins, kernels, streams,
  or device APIs.
- Prove physical memory residency.
- Claim native performance or vendor-library parity.

## Proposal

Introduce `RuntimeLayoutConversionGatePromotionPolicyReport` with schema
`schemas/runtime_layout_conversion_gate_promotion_policy_report.v0.schema.json`.

The report records:

- target graph, artifact kind, and artifact ID;
- readiness contract, schema, status, target gate status, and metadata digest;
- digest-binding artifact ID;
- policy status;
- promotion scope;
- enforcement status;
- required next action;
- derived issues;
- blocked execution surfaces.

The current policy ID is
`runtime_layout_conversion_gate_promotion_policy_mixed`.

## Invariants

- The target graph must be `runtime_mixed_backend_equivalence`.
- The target artifact kind must be `runtime_layout_conversion_evidence`.
- The target artifact ID must be `runtime_layout_conversion_evidence_mixed`.
- Source readiness must be `ready`.
- Source readiness target gate status must remain
  `optional_matrix_inventory_not_gate_required`.
- The digest-binding artifact ID must be
  `runtime_layout_conversion_digest_binding_mixed`.
- Enforcement status must remain `not_enforced` in this report.
- Issues must be derived from report fields.

## Compatibility

This is additive. It does not change Runtime Evidence Matrix requirements or
Runtime Evidence Gate behavior.

## Testing

The v0 implementation adds:

- a deterministic example and golden report;
- schema checks for constants, fail-closed objects, and forbidden fields;
- negative tests for not-ready readiness, wrong digest-binding artifact ID,
  forged issues, and forbidden execution surface text.

## Open Questions

- Should the next gate-enforcement change apply only to the mixed graph first?
- Should TUC define a general per-graph evidence-promotion registry before the
  first enforcement change?
