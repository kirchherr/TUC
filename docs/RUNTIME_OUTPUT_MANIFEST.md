# Runtime Output Manifest

Runtime Output Manifest v0 is a schema-versioned, data-only review artifact for
terminal graph outputs produced by Runtime Executor v0.

## Contract

- Report schema: `schemas/runtime_output_manifest_report.v0.schema.json`
- Report schema version: `tuc.runtime_output_manifest_report.v0`
- Manifest contract: `runtime_output_manifest.data_only.v0`
- Executor contract: `runtime_executor.trusted_backend.v0`
- Store contract: `runtime_tensor_store.internal.v0`
- Value record contract: `runtime_value_record.internal.v0`
- Terminal output policy: `graph_terminal_outputs`
- Raw value policy: `omitted_by_policy`

## What It Proves

The manifest derives terminal outputs from the graph structure, then checks the
Runtime Tensor Store records for those outputs:

- terminal outputs are graph outputs not consumed by later operations
- each terminal output has a runtime record
- output shape and dtype match the executor value contract
- output role is `computed`
- output producer kind is `operation`
- output producer id matches the producing operation
- output records are read-only
- raw tensor values are omitted by policy

The deterministic example is:

```bash
python examples/runtime_output_manifest.py
```

The CI-facing composition point is:

```bash
python examples/runtime_evidence_gate.py
```

Golden evidence:

```text
tests/golden/runtime_output_manifest/proof_of_execution.json
```

Gate golden:

```text
tests/golden/proofs/runtime_evidence_gate.txt
```

## Security Boundary

Runtime Output Manifest is metadata only. It does not serialize tensor values,
hash tensor contents, expose host paths, name device identifiers, reference
generated code, load artifacts, discover plugins, run JIT code, spawn
subprocesses, or touch the network.

The output metadata digest covers terminal output metadata only: tensor name,
shape, dtype, role, producer kind, producer id, read-only status, and raw-value
omission status.

## Current Limitations

- The manifest tracks Runtime Executor v0 only.
- The current runtime output dtype is `float64`.
- The manifest identifies terminal graph outputs, not user-defined API return
  aliases.
- The manifest is not a correctness proof by itself; it complements proof
  reference checks, execution traces, and Runtime Tensor Store Evidence.
