# RFC 0091: Runtime Evidence Gate

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha

## Summary

Add a CI-facing Runtime Evidence Gate that composes the current Runtime Evidence
Matrix and Runtime Executor Conformance.

## Motivation

Runtime Evidence Matrix v0 tracks whether accepted graph fixtures have complete
proof/runtime evidence. Runtime Executor Conformance v0 tracks whether the
fixed trusted executor registry behaves according to its declared support
surface.

These checks are stronger when they run together in CI. A runtime evidence
change should not pass the main `python` job unless both the accepted evidence
inventory and the trusted executor registry are healthy.

## Decision

Add:

- `build_current_runtime_evidence_matrix_report()`
- `examples/runtime_evidence_gate.py`
- `tests/golden/proofs/runtime_evidence_gate.txt`
- `tests/test_runtime_evidence_gate.py`
- [Runtime Evidence Gate](../docs/RUNTIME_EVIDENCE_GATE.md)

Update `.github/workflows/ci.yml` so the main `python` job runs:

```text
python examples/runtime_evidence_gate.py
```

## Security Model

The gate composes existing bounded checks. It does not scan repositories,
discover plugins, import backend modules, access devices, load dynamic
libraries, spawn subprocesses, run JIT code, touch the network, execute
generated artifacts, load raw benchmark output, or approve external executable
backends.

The output is a deterministic text report with status `PASS` only when the
matrix is complete and runtime executor conformance passes.

## Consequences

- CI now catches runtime-evidence incompleteness and trusted executor drift
  outside the full pytest suite.
- The curated current evidence matrix becomes a reusable package API instead of
  living only inside an example script.
- Future graph fixtures and executor changes must keep the gate passing.

## References

- [Runtime Evidence Gate](../docs/RUNTIME_EVIDENCE_GATE.md)
- [Runtime Evidence Matrix](../docs/RUNTIME_EVIDENCE_MATRIX.md)
- [Runtime Executor Conformance](../docs/RUNTIME_EXECUTOR_CONFORMANCE.md)
- `examples/runtime_evidence_gate.py`
- `tests/golden/proofs/runtime_evidence_gate.txt`
