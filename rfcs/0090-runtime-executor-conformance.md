# RFC 0090: Runtime Executor Conformance

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Alpha

## Summary

Add a deterministic conformance report for the fixed trusted Runtime Executor
registry.

## Motivation

Runtime Evidence Matrix v0 proves that accepted graph fixtures have HAC-IR,
runtime-plan, compiler-decision, execution-readiness, execution-trace, and
correctness evidence.

The next practical risk is executor drift: the trusted registry could expose a
backend as evidence while its supported operation set or rejection behavior no
longer matches the contract.

Runtime Executor Conformance v0 checks that:

- `linear-sim` executes only the operation families it declares
- `reference-cpu` executes the full MVP operation-family set
- unsupported operation families are rejected instead of executed silently
- the conformance output is bounded, schema-versioned, and golden-tested

## Decision

Add:

- `src/tuc/runtime/conformance.py`
- `examples/runtime_executor_conformance.py`
- `schemas/runtime_executor_conformance_report.v0.schema.json`
- `tests/golden/runtime_executor_conformance/trusted_runtime_executor_registry.json`
- `tests/test_runtime_executor_conformance.py`
- `tests/test_runtime_executor_conformance_schema.py`
- [Runtime Executor Conformance](../docs/RUNTIME_EXECUTOR_CONFORMANCE.md)

The report uses the contract
`runtime_executor_conformance.trusted.v0` and schema
`schemas/runtime_executor_conformance_report.v0.schema.json`.

## Security Model

The conformance runner uses fixed in-memory operation fixtures and the existing
trusted in-process executor registry. It does not add backend discovery,
dynamic imports, dynamic libraries, device access, subprocesses, JIT, network
access, generated-artifact execution, host-path reads, command-line capture, or
raw benchmark output.

Report fields are bounded identifiers and derived status facts. Issues are
derived from checked cases; arbitrary issue text cannot be injected as evidence.

## Consequences

- Runtime backend support and rejection behavior becomes a golden-tested review
  artifact.
- Future executor registries have a concrete compatibility bar.
- Unsupported execution paths remain visible as rejections instead of hidden
  fallbacks.
- The report still does not authorize executable external backends.

## References

- [Runtime Executor Conformance](../docs/RUNTIME_EXECUTOR_CONFORMANCE.md)
- [Runtime Executor v0](../docs/RUNTIME_EXECUTOR.md)
- [Runtime Evidence Matrix](../docs/RUNTIME_EVIDENCE_MATRIX.md)
- `schemas/runtime_executor_conformance_report.v0.schema.json`
- `tests/golden/runtime_executor_conformance/trusted_runtime_executor_registry.json`
