# RFC 0145: Runtime Backend Equivalence Portfolio Policy

## Status

Accepted.

## Context

Runtime Backend Equivalence Portfolio v0 aggregates multiple trusted
backend-equivalence reports into one backend-diversity artifact. Runtime
Evidence Gate binds that portfolio back to the exact reports checked during
the same invocation, and Runtime Evidence Matrix inventories the portfolio as
scoped evidence.

The remaining gap is that the accepted portfolio membership lived mostly in
gate constants. A reviewer could see that the portfolio passed, but not a
schema-versioned policy artifact declaring which slices and backend sequences
currently define the accepted backend-diversity proof set.

## Decision

Introduce Runtime Backend Equivalence Portfolio Policy v0.

The policy is a data-only artifact with schema:

```text
schemas/runtime_backend_equivalence_portfolio_policy_report.v0.schema.json
```

It declares:

- portfolio ID
- accepted slice IDs and graph names
- baseline and candidate run IDs
- baseline and candidate backend sequences
- minimum comparison counts
- required candidate backend families
- raw-value omission policy
- trusted executor registry

The deterministic example is:

```text
examples/runtime_backend_equivalence_portfolio_policy.py
```

The deterministic golden is:

```text
tests/golden/runtime_backend_equivalence/portfolio_policy_report.json
```

Runtime Evidence Gate now verifies the checked portfolio against this policy
before portfolio evidence can count as passing merge evidence.

## Security Boundary

This policy is metadata-only. It does not execute reports, resolve artifact IDs
to paths, discover backends, load plugins, access devices, spawn subprocesses,
touch the network, run JIT code, load dynamic libraries, execute generated
artifacts, or authorize native execution.

It does not serialize tensor values, tensor-value digests, runtime handles,
host paths, device identifiers, generated code, commands, plugin entrypoints,
benchmark output, backend artifacts, or raw execution output.

## Consequences

The current backend-diversity proof set is now explicit:

- `runtime_backend_equivalence`
- `runtime_vector_backend_equivalence`
- `runtime_mixed_backend_equivalence`

Adding or removing a backend-equivalence slice now requires changing the
policy artifact, schema/golden tests, Matrix inventory, and Runtime Evidence
Gate binding together.
