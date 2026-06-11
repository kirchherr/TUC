# Runtime Reference Correctness

Runtime Reference Correctness v0 is a schema-versioned, data-only review
artifact for comparing terminal Runtime Executor outputs against independent
reference tensors.

## Contract

- Report schema:
  `schemas/runtime_reference_correctness_report.v0.schema.json`
- Report schema version: `tuc.runtime_reference_correctness_report.v0`
- Correctness contract: `runtime_reference_correctness.data_only.v0`
- Executor contract: `runtime_executor.trusted_backend.v0`
- Output manifest contract: `runtime_output_manifest.data_only.v0`
- Raw value policy: `omitted_by_policy`
- Default tolerance: `rtol=1e-12`, `atol=1e-12`

## What It Proves

The report compares terminal graph outputs against explicitly supplied
reference tensors, then serializes only comparison metadata:

- terminal output tensor name
- expected, output, and reference shapes
- expected, output, and reference dtypes
- comparison tolerances
- comparison status
- omitted-value policy for both output and reference tensors
- derived issue list

The deterministic example is:

```bash
python examples/runtime_reference_correctness.py
```

The CI-facing composition point is:

```bash
python examples/runtime_evidence_gate.py
```

Golden evidence:

```text
tests/golden/runtime_reference_correctness/proof_of_execution.json
```

Gate golden:

```text
tests/golden/proofs/runtime_evidence_gate.txt
```

## Security Boundary

Runtime Reference Correctness reads output and reference arrays only to compare
them in memory. It does not serialize tensor values, tensor-value hashes,
elementwise errors, max-error magnitudes, host paths, device identifiers,
generated code, plugin entrypoints, benchmark samples, commands, environment
variables, or executable artifacts.

The comparison metadata digest covers metadata only: tensor name, shapes,
dtypes, tolerances, status, and value-omission policies.

## Current Limitations

- The report tracks Runtime Executor v0 terminal outputs only.
- The current runtime and reference dtype is `float64`.
- The report proves equality within the configured tolerance for the supplied
  reference tensors; it does not prove native backend correctness or native
  performance.
- Future multi-output user APIs may add explicit output aliases, but v0 derives
  outputs from terminal graph tensors.
