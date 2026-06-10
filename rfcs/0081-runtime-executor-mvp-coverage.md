# RFC 0081: Runtime Executor MVP Coverage

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha

## Summary

Execute the Triton-like MVP metadata graph through Runtime Executor v0 and add a
deterministic execution-trace golden.

## Motivation

`proof_of_execution` proves controlled runtime execution on a small graph. The
next practical check is that the same executor path covers every MVP operation
family already represented in the Triton-like metadata graph:

```text
matmul -> softmax -> matmul -> reduction -> elementwise
```

## Decision

Update `examples/triton_mvp_metadata.py` so `run_report()` executes the compiled
HAC-IR graph through `execute_graph(...)`.

Add execution-trace golden:

```text
tests/golden/execution_traces/triton_metadata_mvp_families.txt
```

The trace records:

- `linear-sim` executing matmul and reduction operations
- `reference-cpu` executing softmax and elementwise fallback operations
- planned backend and actual trusted executor for every operation
- output shapes and dtypes for every step

## Security Model

This does not add plugin discovery, backend artifact loading, device access,
subprocesses, dynamic imports, dynamic libraries, JIT execution, network access,
or generated-artifact execution.

Execution remains limited to the fixed trusted runtime executor registry from
RFC 0080.

## Consequences

- The MVP frontend-originated graph is now compileable, plannable, executable,
  traceable, and checkable against independent reference semantics.
- Runtime Executor v0 has golden evidence for all MVP operation families.
- Future executable backend work can build on a practical, already-tested
  execution surface without weakening the plugin boundary.

## References

- [Runtime Executor v0](../docs/RUNTIME_EXECUTOR.md)
- [Frontend Adapter](../docs/FRONTEND_ADAPTER.md)
- `examples/triton_mvp_metadata.py`
- `tests/golden/execution_traces/triton_metadata_mvp_families.txt`
