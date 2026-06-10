# Runtime Evidence Gate

Runtime Evidence Gate v0 is the CI-facing check that combines the current
runtime evidence inventory with trusted executor conformance.

It runs:

- `build_current_runtime_evidence_matrix_report()`
- `run_runtime_executor_conformance()`
- `examples/runtime_evidence_gate.py`

The gate passes only when:

- the Runtime Evidence Matrix is complete across accepted graph fixtures
- Runtime Executor Conformance passes for the fixed trusted executor registry

Golden output:

```text
tests/golden/proofs/runtime_evidence_gate.txt
```

CI entry:

```text
.github/workflows/ci.yml
```

## Security Boundary

The gate does not scan the repository, discover backends, import plugins,
access devices, load dynamic libraries, spawn subprocesses, run JIT code, touch
the network, execute generated artifacts, capture command lines, load raw
benchmark output, or authorize external executable backends.

It composes two bounded in-repository checks:

- data-only evidence identifiers from Runtime Evidence Matrix v0
- fixed in-memory operation fixtures from Runtime Executor Conformance v0

The output is a small deterministic text report ending in `PASS`.

## Review Meaning

This gate is not a native performance claim. It is a merge-time confidence
check that the accepted proof fixtures still have complete runtime evidence and
that the trusted executor registry still matches its declared support surface.
