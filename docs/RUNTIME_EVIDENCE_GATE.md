# Runtime Evidence Gate

Runtime Evidence Gate v0 is the CI-facing check that combines the current
runtime evidence inventory, trusted executor conformance, Runtime Tensor Store
Evidence, Runtime Output Manifest evidence, Runtime Output Contract evidence,
Runtime Public Output Bundle evidence, and Runtime Reference Correctness
evidence.

It runs:

- `build_current_runtime_evidence_matrix_report()`
- `run_runtime_executor_conformance()`
- `build_tensor_store_evidence_report()`
- `build_output_manifest_report()`
- `build_output_contract_report()`
- `build_public_output_bundle()`
- `build_reference_correctness_report()`
- `examples/runtime_evidence_gate.py`

The gate passes only when:

- the Runtime Evidence Matrix is complete across accepted graph fixtures
- Runtime Executor Conformance passes for the fixed trusted executor registry
- Runtime Tensor Store Evidence passes for the current proof-of-execution
  record boundary
- Runtime Output Manifest passes for terminal proof-of-execution outputs
- Runtime Output Contract passes for explicit public output aliases on the
  multi-output runtime fixture
- Runtime Public Output Bundle resolves those aliases to read-only runtime
  values without serializing tensor values into review evidence
- Runtime Reference Correctness passes for terminal proof-of-execution outputs
  against independent reference tensors

Runtime Output Manifest schema:

```text
schemas/runtime_output_manifest_report.v0.schema.json
```

Runtime Output Contract schema:

```text
schemas/runtime_output_contract_report.v0.schema.json
```

Runtime Public Output Bundle schema:

```text
schemas/runtime_public_output_bundle_report.v0.schema.json
```

Runtime Reference Correctness schema:

```text
schemas/runtime_reference_correctness_report.v0.schema.json
```

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

It composes bounded in-repository checks:

- data-only evidence identifiers from Runtime Evidence Matrix v0
- fixed in-memory operation fixtures from Runtime Executor Conformance v0
- data-only Runtime Tensor Store record metadata with raw tensor values omitted
  by policy
- data-only Runtime Output Manifest metadata for terminal graph outputs with raw
  tensor values omitted by policy
- data-only Runtime Output Contract metadata for public output aliases with raw
  tensor values omitted by policy
- Runtime Public Output Bundle metadata for read-only public output values with
  raw tensor values omitted by policy
- data-only Runtime Reference Correctness metadata with output and reference
  tensor values omitted by policy

The output is a small deterministic text report ending in `PASS`.

## Review Meaning

This gate is not a native performance claim. It is a merge-time confidence
check that the accepted proof fixtures still have complete runtime evidence and
that the trusted executor registry still matches its declared support surface.
