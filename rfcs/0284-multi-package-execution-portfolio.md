# RFC 0284: Multi-Package Execution Portfolio v0

Status: Accepted

## Summary

Compose two exact Backend Package Execution Admissions into one no-fallback
heterogeneous portfolio. Project every package-owned assignment to a fixed
trusted executor, retain layout-conversion evidence, execute the projected
plan, and require Runtime Backend Equivalence against `reference-cpu`.

## Motivation

RFC 0283 proved a controlled bridge from one external capability package to a
trusted executor, but its proof graph still used `reference-cpu` for `matmul`.
That leaves the stronger Universal Compute question open: can multiple
independent capability descriptions jointly own an entire graph without a
built-in CPU assignment becoming the implicit center?

The smallest useful answer requires two packages with different operation and
layout behavior, an actual boundary between them, trusted execution, and an
independent semantic baseline.

## Decision

Add:

- `docs/BACKEND_PACKAGE_EXECUTION_PORTFOLIO.md`
- `examples/backend_package_execution_portfolio.py`
- `examples/backend_packages/external_systolic.v0.json`
- `schemas/backend_package_execution_portfolio_report.v0.schema.json`
- `tests/golden/backend_integration_package/external_systolic_report.json`
- `tests/golden/backend_package_execution_portfolio/proof_report.json`
- `rfcs/0284-multi-package-execution-portfolio.md`

Extend the maintainer-owned execution binding registry with an exact binding
from `external-systolic-reference-package` to `systolic-sim`. Its admitted
scope is `matmul` in `device_sram`, accepting `row_major` and producing
`blocked`.

Compose that admission with the existing `external-vector-reference-package`
binding. The source plan must be:

```text
external-systolic -> external-vector
```

The trusted projection must be:

```text
systolic-sim -> vector-sim
```

The intermediate `projection` tensor must retain explicit
`blocked -> row_major` layout-conversion evidence. Runtime Backend Equivalence
must pass against the all-`reference-cpu` baseline.

## Portfolio Invariants

- The v0 required package-ID set is exact.
- At least two admissions are required.
- Every admission must independently allow trusted projection.
- Package IDs, backend names, binding IDs, and executor names are unique.
- Admitted operation scopes do not overlap.
- Every source-plan assignment names one admitted package backend.
- Every admitted package is used by the source plan.
- Every operation remains inside its package's admitted operation scope.
- Runtime overrides and candidate-score payloads are rejected.
- Transfer edges are projected only through admitted bindings.
- Layout conversions are preserved unchanged.
- The complete source plan must equal a canonical plan reconstructed from the
  maintainer-owned binding capabilities; forged placement or movement metadata
  is rejected before projection.
- Runtime readiness passes before execution.

## Trust Model

Both packages are attacker-controlled data. All execution bindings remain
maintainer-owned and bind exact package, capability, and executor-contract
digests. Packages cannot add mappings, imports, code, paths, commands, handles,
or artifacts.

Composition is a new trust decision, not an automatic consequence of two
single-package admissions. The portfolio therefore rejects overlapping
operation authority, duplicate identities, partial package sets, fallbacks,
and unbound plan content.

## Evidence Invariants

- Source and projected plans have separate SHA-256 digests.
- Both source package identities and trusted executor identities remain visible.
- Package and executor counts remain visible.
- Fallback assignment count is exactly zero.
- Layout conversion metadata and byte count remain visible.
- Runtime step and terminal output metadata remain visible.
- Backend Equivalence must pass.
- Raw values, source, paths, commands, runtime handles, device IDs, and backend
  artifacts are not serialized.
- The JSON schema rejects additional properties at every object boundary.

## Security Consequences

External implementation execution, plugin discovery, dynamic import, native
library loading, generated-artifact execution, JIT, subprocess, network, and
physical device access remain blocked. The trusted simulators execute fixed
in-repository reference semantics only.

The new package does not broaden the plugin lifecycle policy or create a
generic package registry. Any package, operation-scope, digest, or executor
change requires explicit code, RFC, golden, and negative-test review.

## Alternatives Rejected

### Keep `reference-cpu` as the matmul assignment

Rejected because it would repeat the single-package proof and leave fallback
as the hidden center of the graph.

### Allow overlapping package operation scopes

Rejected in v0 because selection authority would become ambiguous and require
a separate deterministic portfolio policy and evidence model.

### Accept arbitrary admitted-package sets

Rejected because individual admission does not prove safe composition. V0
proves one exact portfolio before generalizing the policy.

### Execute package implementations

Rejected because it would introduce plugin and native-code attack surfaces
outside the accepted security model.

### Claim physical heterogeneous execution

Rejected because `systolic-sim` and `vector-sim` are trusted semantic
executors. The proof concerns abstraction, planning, composition, and
correctness, not device residency or native performance.

## Consequences

TUC now demonstrates a no-fallback, multi-package path from external capability
data through heterogeneous planning, explicit layout conversion, digest-bound
trust projection, runtime execution, and semantic equivalence. This materially
advances Master Plan Milestones 3 and 4 while keeping native execution and
performance claims explicitly open.
