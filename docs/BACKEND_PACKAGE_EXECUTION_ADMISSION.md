# Backend Package Execution Admission

Backend Package Execution Admission v0 connects the portable data-only backend
package to actual TUC Runtime Executor behavior without loading or executing
package-supplied code. It is a narrow trusted-reference projection, not a
general plugin mechanism.

## Research Question

Can a backend described outside TUC core participate in a heterogeneous runtime
proof while its implementation remains untrusted and unexecuted?

For the bounded reference package, the current answer is yes:

```text
external package
    -> capability and planning conformance
    -> digest-bound maintainer allowlist
    -> trusted executor capability match
    -> source plan: reference-cpu -> external-vector
    -> projected plan: reference-cpu -> vector-sim
    -> trusted runtime execution
    -> reference-cpu equivalence
    -> PASS
```

The runnable proof is `examples/backend_package_execution_proof.py`.

## Admission Boundary

Admission requires exact agreement across:

- package ID, package digest, and capability-manifest digest;
- canonical re-evaluation of the supplied integration report from the package;
- package backend name and admitted operation family;
- memory domain, supported layouts, and produced layouts;
- a fixed maintainer-owned binding ID;
- the selected executor's presence in the fixed trusted registry;
- the trusted executor contract digest and built-in capability envelope.

Any package or executor drift produces a structured `BLOCKED` report. A package
cannot grant itself admission: the binding lives in TUC code and is recorded by
`rfcs/0283-backend-package-execution-admission.md`.

## Plan Projection

The compiler first creates a plan against the package capability. Projection
then replaces only the admitted package backend identity with its fixed trusted
executor identity. Existing trusted assignments remain unchanged, and transfer
edges are projected consistently.

Runtime overrides and candidate-score payloads are rejected in v0. Unknown
non-package backends, plans without an admitted package assignment, operation
scope expansion, and mismatched graph assignments fail closed before runtime
execution.

The source and projected plans receive separate SHA-256 digests in the proof
report, so the trust transition remains reviewable.

## Execution And Equivalence

The reference graph contains `matmul -> elementwise`:

- `matmul` remains on `reference-cpu`;
- `elementwise` is planned for `external-vector`;
- admission projects that operation to the pre-registered `vector-sim` executor;
- the host-to-device-SRAM transfer edge remains explicit;
- terminal output semantics are compared with an all-`reference-cpu` run.

Only output names, shapes, dtypes, plan digests, backend sequences, step counts,
transfer counts, and equivalence metadata are serialized. Raw tensor values are
omitted.

## Security Properties

- No plugin discovery or dynamic import.
- No package backend implementation execution.
- No native library, generated artifact, JIT, network, subprocess, or device
  access.
- No package-controlled executor mapping or filesystem path.
- Exact digest pinning before projection.
- Fixed built-in executor registry and capability compatibility checks.
- Plain mapping requirement for runtime inputs.
- Deterministic fail-closed admission and proof reports.

## Run

```bash
python examples/backend_package_execution_proof.py
```

## Artifacts

- Admission schema: `schemas/backend_package_execution_admission_report.v0.schema.json`
- Proof schema: `schemas/backend_package_execution_proof_report.v0.schema.json`
- Admission golden: `tests/golden/backend_package_execution/admission_report.json`
- Proof golden: `tests/golden/backend_package_execution/proof_report.json`
- Entrypoint: `examples/backend_package_execution_proof.py`
- Decision record: `rfcs/0283-backend-package-execution-admission.md`
- This guide: `docs/BACKEND_PACKAGE_EXECUTION_ADMISSION.md`

## Non-Claims

This proof does not execute an external plugin, package backend implementation,
native artifact, GPU kernel, or physical accelerator. It does not establish a
stable ABI, sandbox, device integration, native performance, or production
backend certification. It proves the controlled trust transition from external
capability data to an already trusted semantic executor.
