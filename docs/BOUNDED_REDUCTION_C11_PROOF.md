# Bounded Reduction C11 Proof

This experiment adds a second source program to the native research path:

```text
fixed inert matmul_reduction source
  -> existing research parser
  -> exact typed Source Intent
  -> generated C11 matmul and axis-1 sum
  -> static x86_64 executable in scratch
  -> independent reference check
```

The earlier source-to-two-target proof covers Matmul-plus-ReLU. Here the
terminal tensor changes rank: `A[4,8] @ B[8,2]` is reduced over axis 1 to
`y[4]`. ReLU must not be inserted. The inputs include both signs, and the
fixed expected output is `[-5.875, 2.625, 5.125, 4.75]`.

## Reproduce

With the repository's Linux Python dependencies installed, verify review-time
parsing and deterministic code generation:

```bash
PYTHONPATH=.:src python examples/bounded_reduction_c11.py
```

That command only verifies artifacts; its output is an emission plan, not
execution evidence. To explicitly build and run the reviewed native experiment
on a disposable Linux x86_64 Docker host:

```bash
PYTHONPATH=.:src sh scripts/run_bounded_reduction_c11_proof.sh
```

The script builds three images from the existing pinned GCC base, runs a
zero-call preflight and the static program, then runs an ASan/UBSan build.
Three wrong-code binaries must each return a reference mismatch: lost
accumulation, accidental ReLU and wrong reduction indexing. The unchanged
harness compares all four outputs to fixed expectations and a differently
structured binary64 reference. Python separately checks an exact rational
reference. The sanitizer options follow the
[GCC instrumentation documentation](https://gcc.gnu.org/onlinedocs/gcc-14.1.0/gcc/Instrumentation-Options.html).

Execution uses no device, network or host mount. Containers run as UID/GID
10001, read-only, with no capabilities, no-new-privileges, default seccomp,
128 MiB memory, one CPU and eight PIDs. A worker alarm and an operator timeout
bound execution; the named container is removed on exit. Compiler images may
need downloading during the explicit build. Unprivileged containers still
share the host kernel and are not a proof against kernel vulnerabilities.

## Evidence And Limits

- Decision: `rfcs/0305-bounded-reduction-c11-proof.md`.
- Emitter: `examples/bounded_reduction_c11.py`.
- Generated code and plan: `docker/reduction-c11/`.
- Closed worker schema: `schemas/bounded_reduction_c11_observation.v0.schema.json`.
- Tests: `tests/test_bounded_reduction_c11.py`.
- Native execution: the `Bounded C11 proof` workflow's second-source step.
- Accepted native observation: `tests/golden/proofs/bounded_reduction_c11_observation.json`.

The first native run passed on 2026-09-09 at implementation commit
`3873291f586a97ec33a800d76c61bc30c3646aa6`: zero-call preflight, two-call
static execution, ASan/UBSan execution, and all three wrong-code rejections.
See the [observed CI job](https://github.com/kirchherr/TUC/actions/runs/34368239919/job/102522443572).
The checked-in observation reproduces that job's static execution output;
the CI job is its provenance, not an independent organization or attestation.

Only a completed native workflow establishes execution for its commit. An
emission plan or synthetic test observation does not. Public worker output
contains shapes, digests, call counts and correctness status, without source,
raw values, machine identifiers or timings. Three runtime variants are test
artifacts and never become accepted evidence.

This C11 observation remains one additional fixed source case, same-maintainer,
on one target. RFC 0306 separately records actual execution of the same
reduction on physical CUDA; see [the CUDA proof](BOUNDED_REDUCTION_CUDA_PROOF.md).
Neither experiment establishes arbitrary vendors or ISAs,
performance, independent reproduction, arbitrary source support or production
runtime admission. The normal executor and existing acceptance gates are
unchanged. The next useful experiment broadens the reviewed input vector or
shape and executes both targets.
