# Backend Package Execution Portfolio

Backend Package Execution Portfolio v0 composes two independently validated,
data-only backend packages into one heterogeneous execution proof. Every graph
assignment must be owned by an admitted package; CPU fallback and unbound
backend identities are rejected.

## Research Question

Can independently described hardware capability domains cooperate on one
compute graph while TUC preserves explicit planning boundaries, trusted
execution, and observable semantics?

For the bounded v0 portfolio, the answer is yes:

```text
external-systolic package      external-vector package
          |                              |
          +---- exact digest admission --+
                         |
       source plan: external-systolic -> external-vector
                         |
            blocked -> row_major conversion
                         |
       trusted plan: systolic-sim -> vector-sim
                         |
              controlled runtime execution
                         |
               reference-cpu equivalence
                         |
                        PASS
```

The runnable proof is `examples/backend_package_execution_portfolio.py`.

## Package Portfolio

The v0 portfolio is deliberately exact rather than open-ended:

- `external-systolic-reference-package` admits only `matmul` and projects to
  `systolic-sim`;
- `external-vector-reference-package` admits only `elementwise` and projects
  to `vector-sim`;
- operation scopes must be non-empty and disjoint;
- package IDs, backend names, binding IDs, and trusted executors must be unique;
- the complete required package set must be present and admitted.

The systolic package is declared in
`examples/backend_packages/external_systolic.v0.json`. Its package and
capability digests are fixed in maintainer-owned code. Neither package can
provide an executor mapping or executable implementation.

## No-Fallback Plan

The proof graph contains `matmul -> elementwise`. Compilation against both
package capabilities produces:

```text
external-systolic -> external-vector
```

The portfolio rejects a source plan containing `reference-cpu`, an unknown
backend, a package outside its admitted operation scope, an unused admitted
package, runtime overrides, or candidate-score payloads. Transfer-edge backend
identities are projected through the same fixed bindings.

## Layout Boundary

`external-systolic` produces the intermediate tensor in `blocked` layout while
`external-vector` accepts `row_major`. Both use `device_sram`, so no
cross-domain transfer is needed, but the compiler emits an explicit 32-byte
layout conversion:

```text
projection: blocked -> row_major
```

The projected trusted plan retains this conversion. The proof report records
the tensor, target operation, layouts, and byte count without serializing a
tensor value or runtime handle.

## Trusted Execution And Equivalence

Only after exact package admission does TUC project the source plan to:

```text
systolic-sim -> vector-sim
```

Both executors already exist in the fixed trusted Runtime Executor registry.
The graph is executed with deterministic finite inputs and compared with an
all-`reference-cpu` run through Runtime Backend Equivalence. A portfolio proof
can be serialized only when equivalence passes.

## Security Properties

- No package code, plugin, entry point, dynamic import, or native library.
- No package-controlled executor mapping.
- No JIT, generated artifact, subprocess, network, or device access.
- Exact package, capability, and executor-contract digests.
- Exact package-set and operation-scope composition.
- No fallback or unbound source-plan assignments.
- Canonical source-plan reconstruction from maintainer-owned capabilities blocks
  forged memory domains, layouts, movement costs, transfers, or conversions.
- No runtime overrides or candidate-score payloads in v0.
- Bounded, source-free, raw-value-free JSON evidence.
- Fail-closed schema with unknown fields rejected.

## Run

```bash
python examples/backend_package_execution_portfolio.py
```

## Artifacts

- Guide: `docs/BACKEND_PACKAGE_EXECUTION_PORTFOLIO.md`
- Entrypoint: `examples/backend_package_execution_portfolio.py`
- Systolic package: `examples/backend_packages/external_systolic.v0.json`
- Report schema: `schemas/backend_package_execution_portfolio_report.v0.schema.json`
- Systolic integration golden: `tests/golden/backend_integration_package/external_systolic_report.json`
- Portfolio proof golden: `tests/golden/backend_package_execution_portfolio/proof_report.json`
- Decision record: `rfcs/0284-multi-package-execution-portfolio.md`

## Non-Claims

This proof does not execute external package code, a native plugin, a GPU
kernel, or a physical accelerator. `device_sram` and layout placement are
planning semantics, not proof of physical residency. It does not establish
native performance, production sandboxing, a stable plugin ABI, or arbitrary
third-party package admission.

It proves a narrower and strategically important statement: two independently
declared capability packages can own every operation in one graph, cross an
explicit layout boundary, execute through trusted heterogeneous semantics, and
preserve terminal behavior without changing HAC-IR.
