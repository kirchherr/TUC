# RFC 0216: Runtime Layout Conversion Gate Enforcement

## Status

Accepted

## Summary

Promote `runtime_layout_conversion_evidence_mixed` from review inventory to
Runtime Evidence Gate-required evidence for `runtime_mixed_backend_equivalence`.

## Motivation

The mixed backend-equivalence slice is the first place where TUC demonstrates a
non-trivial layout transition across backend capabilities. If that transition is
only explained by planning text, the abstraction can still leak silently: the
proof says two backends compose, but reviewers cannot verify that the required
layout movement is bound to the accepted plan.

## Proposal

- Add `runtime_layout_conversion_evidence` to the mixed backend-equivalence
  graph's `required_artifact_kinds` in Runtime Evidence Matrix.
- Add `runtime_layout_conversion_evidence_mixed` to the exact Matrix binding
  used by Runtime Evidence Gate Matrix Coverage.
- Make Runtime Evidence Gate evaluate Runtime Layout Conversion Evidence,
  Mixed Tensor Store Evidence, Runtime Layout Conversion Digest Binding,
  Runtime Layout Conversion Gate Readiness, and Runtime Layout Conversion Gate
  Promotion Policy before the gate can pass.
- Keep the enforcement graph-scoped to `runtime_mixed_backend_equivalence`.

## Invariants

- The layout-conversion report graph must be `runtime_mixed_backend_equivalence`.
- The report must omit raw values and must not execute converters.
- Conversion count and planned bytes must match Mixed Planning Explanation.
- Conversion count and planned bytes must match HS-IR Plan Alignment.
- Digest Binding must bind the layout-conversion metadata digest to HS-IR
  Alignment metadata and Mixed Tensor Store metadata.
- Promotion Policy must report
  `enforcement_status: enforced_by_runtime_evidence_gate`.

## Non-Goals

- Execute real layout converters.
- Claim physical residency, stream behavior, device handles, or memory
  addresses.
- Claim native performance or vendor-library parity.
- Generalize layout-conversion requirements to every future graph.

## Testing

- Runtime Evidence Matrix and Runtime Evidence Gate Matrix Coverage goldens are
  updated.
- Runtime Evidence Gate golden now includes explicit layout-conversion evidence,
  digest-binding, readiness, policy, and enforcement lines.
- Negative gate tests reject unbound layout-conversion evidence, unbound digest
  binding, and unbound mixed tensor-store evidence.