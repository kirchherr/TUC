# RFC 0146: Runtime Evidence Gate Artifact-ID Binding

## Status

Accepted.

## Context

Runtime Evidence Matrix v0 records graph evidence as data-only artifact kinds
and artifact IDs. Runtime Evidence Gate already required backend-equivalence
and portfolio graph entries to exist with the expected graph family, source
boundary, scoped required artifact kinds, and completeness status.

That was necessary but not strict enough. A forged or stale matrix entry could
remain complete with the right artifact kind while pointing at a different
concrete evidence artifact ID.

## Decision

Runtime Evidence Gate now binds Matrix coverage for backend-equivalence
evidence to exact artifact IDs:

- `runtime_backend_equivalence_systolic`
- `runtime_backend_equivalence_vector`
- `runtime_backend_equivalence_mixed`

It also binds Backend Equivalence Portfolio Matrix coverage to the exact
portfolio and policy artifact IDs:

- `runtime_backend_equivalence_portfolio`
- `runtime_backend_equivalence_portfolio_policy`

The CI-facing gate report prints these artifact IDs so reviewers can see which
Matrix evidence was accepted.

## Security Boundary

This binding compares bounded identifiers already present in data-only Matrix
records. It does not resolve artifact IDs to paths, read external artifacts,
execute generated files, discover plugins, load backends, access devices,
spawn subprocesses, touch the network, run JIT code, load dynamic libraries, or
authorize native execution.

## Consequences

Backend-equivalence Matrix coverage is no longer kind-only. Changing the
accepted evidence artifact for a backend-equivalence or portfolio slice now
requires a visible change to the Runtime Evidence Gate constants, deterministic
golden output, tests, and documentation.
