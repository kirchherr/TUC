# Runtime Executor Conformance v0

Runtime Executor Conformance v0 checks the fixed trusted in-process executor
registry against its declared operation support.

It is a data-only review artifact. It does not discover backends, import
modules, access devices, spawn subprocesses, load dynamic libraries, run JIT
code, touch the network, execute generated artifacts, or read external backend
files.

## Contract

- Conformance contract: `runtime_executor_conformance.trusted.v0`
- Report schema: `schemas/runtime_executor_conformance_report.v0.schema.json`
- Report schema version: `tuc.runtime_executor_conformance_report.v0`
- Executor contract: `runtime_executor.trusted_backend.v0`
- Executor registry: `trusted_runtime_executor_registry.v0`
- Golden report:
  `tests/golden/runtime_executor_conformance/trusted_runtime_executor_registry.json`
- Example: `examples/runtime_executor_conformance.py`
- CI gate: `examples/runtime_evidence_gate.py`
- Tests: `tests/test_runtime_executor_conformance.py`,
  `tests/test_runtime_executor_conformance_schema.py`

## Checked Cases

The conformance report runs bounded in-memory fixtures for each MVP operation
family against each trusted executor:

- `linear-sim` must execute `matmul` and `reduction`
- `linear-sim` must reject `elementwise` and `softmax`
- `reference-cpu` must execute `matmul`, `elementwise`, `reduction`, and
  `softmax`
- `systolic-sim` must execute `matmul`
- `systolic-sim` must reject `elementwise`, `reduction`, and `softmax`

Executed cases record output shape and dtype. Rejected cases record
`not_executed` and no output shape.

## Security Boundary

The report includes only bounded identifiers, operation-family names, expected
and observed status, output shape, output dtype, the runtime executor contract,
the trusted registry id, and the blocked execution-surface list.

It intentionally excludes:

- source text
- host paths
- command lines
- environment variables
- device identifiers
- plugin entrypoints
- backend artifact contents
- generated code
- raw benchmark output

Issues are derived from observed case status. A report cannot smuggle arbitrary
issue text as evidence.

## Why It Matters

Runtime Evidence Matrix v0 proves that accepted graph fixtures have the right
artifact coverage. Runtime Executor Conformance v0 proves the trusted executor
registry itself still behaves according to its contract.

The CI-facing [Runtime Evidence Gate](RUNTIME_EVIDENCE_GATE.md) requires both
conditions before a runtime evidence change can pass the main `python` job.

This makes future backend work safer: a new executable or external backend path
must first preserve explicit support and rejection behavior before it can be
considered as runtime evidence.
