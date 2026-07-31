# RFC 0283: Backend Package Execution Admission v0

Status: Accepted

## Summary

Introduce a digest-bound admission and trusted-reference projection for one
portable Backend Integration Package. The compiler may plan against the
external package capability, but runtime execution may occur only after TUC
maps the exact allowlisted package identity to a pre-registered trusted
executor with a compatible capability envelope.

## Motivation

RFC 0282 proved that an external developer can describe capability and planning
expectations without modifying TUC core. The next research question is whether
that package can participate in a real heterogeneous execution proof without
turning package validation into arbitrary code execution.

Directly importing package code, accepting an entry point, or loading a native
library would violate the current plugin lifecycle policy and create an
unbounded execution surface. A trusted projection provides a smaller proof: it
tests the package-to-runtime architecture while retaining TUC's fixed reference
semantics and existing Runtime Executor controls.

## Decision

Add:

- `docs/BACKEND_PACKAGE_EXECUTION_ADMISSION.md`
- `examples/backend_package_execution_proof.py`
- `schemas/backend_package_execution_admission_report.v0.schema.json`
- `schemas/backend_package_execution_proof_report.v0.schema.json`
- `tests/golden/backend_package_execution/admission_report.json`
- `tests/golden/backend_package_execution/proof_report.json`
- `rfcs/0283-backend-package-execution-admission.md`

The v0 allowlist binds the exact `external-vector-reference-package` package and
capability digests to the existing `vector-sim` trusted executor. The admitted
scope is `elementwise` in `device_sram` with `row_major` accepted and produced
layouts.

The proof graph is planned as:

```text
reference-cpu -> external-vector
```

Admission projects it to:

```text
reference-cpu -> vector-sim
```

The projected plan executes through the fixed Runtime Executor registry and is
compared with an all-`reference-cpu` baseline through Runtime Backend
Equivalence.

## Trust Model

The package is attacker-controlled data. The execution binding is
maintainer-owned TUC code and cannot be supplied by the package. Admission
requires:

- exact package and capability digests;
- canonical re-evaluation of integration evidence from the bound package;
- exact backend identity and operation scope;
- compatible memory-domain and layout declarations;
- exact trusted executor contract digest;
- executor presence in the fixed trusted registry; and
- capability containment by the built-in trusted executor capability.

The package's backend implementation is never requested, loaded, imported, or
executed.

## Plan Invariants

- Graph and assignment order must agree exactly.
- At least one assignment must use the admitted package backend.
- Every package assignment must remain inside the admitted operation set.
- Every other assignment must already name a trusted executor.
- Transfer-edge backend identities are projected consistently.
- Runtime overrides and candidate-score payloads are rejected in v0.
- Runtime execution readiness must pass on the projected plan before execution.

## Evidence Invariants

- Source and projected plans have separate SHA-256 digests.
- Source and projected backend sequences remain visible.
- Projection and transfer counts remain visible.
- Runtime step count and terminal output metadata remain visible.
- Backend Equivalence must pass before proof serialization.
- Raw tensor values, source, paths, commands, runtime handles, devices, and
  backend artifacts are never serialized.

## Security Consequences

External plugin discovery, external implementation execution, native ABI
loading, generated-artifact execution, JIT, subprocess, network, and physical
device access remain blocked. This RFC does not change Backend Plugin Lifecycle
Policy and does not grant general executable-plugin admission.

Digest updates require an explicit code and golden change. Executor contract or
capability drift blocks admission until reviewed. Unknown packages receive a
structured `package_not_allowlisted` issue.

## Alternatives Rejected

### Import a Python backend from the package

Rejected because validation would become arbitrary host-code execution.

### Accept a package-provided executor mapping

Rejected because an untrusted package could select a more privileged executor
and create a confused-deputy path.

### Rewrite the plan silently

Rejected because the original hardware-independent planning result must remain
reviewable. Both plans and both backend sequences are evidence.

### Claim physical backend execution

Rejected because the current executor uses trusted in-process reference
kernels. The proof is semantic and architectural, not native or physical.

## Consequences

TUC now demonstrates an end-to-end path from a portable external capability
package through heterogeneous planning, explicit trust admission, runtime
execution, and semantic equivalence. Master Plan Milestone 4 advances, but its
native `GPU + Specialized Backend` target remains open.
