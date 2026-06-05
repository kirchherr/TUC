# RFC 0026: Backend Support Diagnostics

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 2

## Summary

TUC adds structured backend support diagnostics to the explicit backend
capability registry.

For a concrete `ComputeOperation`, `BackendRegistry.diagnose_operation_support`
returns one diagnostic per registered backend explaining whether that backend
accepts or rejects the operation through pure capability-data checks.

## Motivation

Backend extensibility needs explainability before cleverness. As soon as TUC
has multiple simulator, GPU, photonic, or neuromorphic backends, maintainers and
backend authors need to know why an operation was eligible or rejected before
runtime partitioning chooses a placement.

Without structured diagnostics, backend capability mismatches risk becoming
opaque strings inside partition plans. That would make security review,
conformance failures, and external backend onboarding harder.

## Decision

Add:

- `BackendSupportDiagnostic`
- `BackendRegistry.diagnose_operation_support`
- Tests for accepted backends, unsupported operation kinds, unsupported layouts,
  invalid error budgets, and excessive error budgets.
- Documentation in `docs/BACKEND_REGISTRY.md` and `docs/BACKEND_API.md`.

Current reason codes:

- `accepted`
- `unsupported_operation_kind`
- `unsupported_layout`
- `invalid_layout_attribute`
- `invalid_error_budget_attribute`
- `error_budget_exceeds_backend_limit`

Diagnostics include backend name, operation name, operation kind, support
status, reason code, and a compact detail string.

## Security Model

Support diagnostics are pure data.

They do not:

- Call backend `lower`.
- Import Python modules.
- Spawn subprocesses.
- Load dynamic libraries.
- Open devices.
- Execute generated artifacts.
- Include host paths, device identifiers, imported module names, or backend
  execution output.

Invalid operation attributes fail closed as unsupported diagnostics.

## Consequences

- Backend author feedback becomes deterministic and testable.
- Future partitioning reports can explain candidate rejection before cost-model
  scoring.
- TUC keeps backend selection inspectable without expanding plugin attack
  surface.

## Follow-Up

1. Thread support diagnostics into compiler-level decision reports.
2. Add machine-readable runtime plan diagnostics once graph partitioning becomes
   cost-model driven.
3. Keep executable plugin lifecycle work behind a separate sandboxing RFC.
