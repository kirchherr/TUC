# RFC 0042: Runtime Manual Override Policy

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Delta

## Summary

TUC defines a runtime manual override policy before adding automatic candidate
scoring, global optimization, or any placement override implementation.

The policy lives in `docs/RUNTIME_OVERRIDE_POLICY.md`.

## Motivation

Runtime planning is a strategic proof asset for TUC. It must stay explainable
as the project moves from rule-based placement toward cost models and future
hardware-specific simulators.

Manual overrides are useful for proof fixtures and backend-author diagnostics,
but they are also risky. A poorly scoped override path could bypass capability
checks, smuggle hardware facts into HAC-IR, hide fallbacks, or create a new
compiler attack surface.

## Decision

Adopt a policy-first gate:

- No manual override implementation is accepted until the override schema,
  validation boundary, diagnostics, and golden artifacts are covered by a
  dedicated implementation RFC.
- Future overrides may constrain only already accepted backend candidates.
- Overrides must be operation-scoped by default.
- Overrides must be schema-versioned, bounded, and declarative.
- Overrides cannot change mathematical semantics, HAC-IR facts, tensor
  contracts, backend capabilities, layouts, or error-budget meaning.
- Override effects must appear in compiler decision reports and runtime-plan
  golden dumps.

## Security Model

Manual override data is untrusted input.

It must not:

- execute backend code
- discover plugins
- import modules
- spawn subprocesses
- load dynamic libraries
- access devices
- execute generated artifacts
- touch the network
- read host paths
- read environment variables
- affect planning before graph, HAC-IR, and capability validation complete

Unknown, contradictory, unsupported, or over-budget override data must fail
closed with bounded diagnostics.

## Consequences

- Automatic global optimization remains blocked until placement controls have
  explicit trust-boundary rules.
- Backend authors get a future path for reviewable placement experiments
  without changing TUC core.
- Maintainers get a checklist for detecting semantic bypasses before override
  code exists.
- Compiler decision reports and runtime-plan goldens become the required
  evidence surface for future override behavior.

## Follow-Up

1. Add a schema-versioned declarative override object only after a dedicated
   implementation RFC.
2. Add negative tests for unknown fields, unknown operations, unknown backends,
   contradictory rules, over-budget data, and unsupported backend assignments.
3. Add decision-report and runtime-plan golden fixtures before allowing
   override-backed examples.
4. Keep candidate scoring independent from hidden manual override side effects.

