# RFC 0043: Runtime Manual Overrides v0

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Delta

## Summary

TUC adds a first schema-versioned manual runtime placement override data model.

The implementation introduces:

- `RuntimeOverrideSet`
- `RuntimeOverrideRule`
- `RuntimeOverrideEffect`
- `RuntimeOverrideAction`
- `RuntimeOverrideError`
- `RUNTIME_OVERRIDE_SCHEMA_VERSION = "tuc.runtime_overrides.v0"`

Override data can be built from bounded declarative manifest data through
`RuntimeOverrideSet.from_manifest(...)` and passed to `partition_graph(...)` or
`compile_graph(...)`.

## Motivation

RFC 0042 required a policy gate before placement overrides, candidate scoring,
or automatic global optimization. This RFC implements the smallest useful
override surface that satisfies that gate without adding plugin discovery,
imports, subprocesses, dynamic libraries, device access, network access, or
generated-artifact execution.

The implementation follows `docs/RUNTIME_OVERRIDE_POLICY.md`.

The goal is reviewability, not performance. Overrides are a way to force or
constrain known placement scenarios for tests, proof fixtures, and backend
author diagnostics.

## Decision

Manual overrides are operation-scoped and support three actions:

- `require_backend`: restrict one operation to one already accepted backend
  candidate.
- `prefer_backend`: select one already accepted backend candidate before normal
  rule-based candidate scoring.
- `deny_backend`: remove one already accepted backend candidate.

The schema is:

```text
tuc.runtime_overrides.v0
```

with manifest shape:

```python
{
    "schema_version": "tuc.runtime_overrides.v0",
    "rules": (
        {
            "operation_name": "projection",
            "action": "require_backend",
            "backend_name": "gpu-matmul",
        },
    ),
}
```

Overrides are validated after graph, HAC-IR, and backend capability data exist,
and before runtime candidate selection is finalized.

## Security Model

Override data is untrusted input. It is parsed as bounded plain `dict`, `list`,
and `tuple` data.

Validation rejects:

- unknown `schema_version`
- unknown fields
- unsupported actions
- unsafe identifiers
- duplicate rules
- multiple required backends for one operation
- multiple preferred backends for one operation
- simultaneous `require_backend` and `prefer_backend` for one operation
- contradictory `require_backend` or `prefer_backend` with `deny_backend`
- unknown operations
- unknown backends
- backends that did not already pass capability support checks
- deny rules that remove every accepted candidate
- rule counts above the override budget

The implementation does not:

- execute backend code
- discover plugins
- import user-controlled modules
- spawn subprocesses
- load dynamic libraries
- access devices
- execute generated artifacts
- touch the network
- read host paths
- read environment variables
- change HAC-IR attributes
- add or modify backend capabilities
- change operation semantics

## Inspectability

Runtime plans now include a `manual_overrides` block when an override affects
placement.

Compiler decision reports include the same override effect next to support
diagnostics and final assignment reasons.

Golden fixtures cover the first required-backend case:

- `tests/golden/runtime_plans/manual_override_require.txt`
- `tests/golden/compiler_decisions/manual_override_require.txt`

## Consequences

- TUC has a safe review surface for manual placement experiments.
- Overrides remain independent from HAC-IR semantics and backend capability
  declarations.
- Candidate scoring and automatic global optimization still need their own
  RFCs before they can use or interact with this mechanism.

## Follow-Up

1. Add manifest file loading only if a dedicated security review approves path,
   file-size, duplicate-key, and provenance controls.
2. Add richer override diagnostics only if they remain bounded and free of host
   paths or backend implementation details.
3. Keep future candidate scoring explainable and golden-tested before enabling
   automatic global optimization.
