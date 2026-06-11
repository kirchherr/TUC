# Runtime Tensor Store Evidence

Runtime Tensor Store Evidence v0 is a schema-versioned, data-only review
artifact for Runtime Tensor Store records.

## Contract

- Report schema: `schemas/runtime_tensor_store_evidence_report.v0.schema.json`
- Report schema version: `tuc.runtime_tensor_store_evidence_report.v0`
- Evidence contract: `runtime_tensor_store_evidence.data_only.v0`
- Store contract: `runtime_tensor_store.internal.v0`
- Value record contract: `runtime_value_record.internal.v0`
- Raw value policy: `omitted_by_policy`

## What It Proves

The report checks that Runtime Executor output exposes the expected internal
Runtime Tensor Store records for a graph:

- external input tensors have `input` records
- operation outputs have `computed` records
- record shapes match graph tensor shapes
- record dtype matches the Runtime Executor `float64` value contract
- record values are read-only
- unexpected records fail evidence review

The deterministic example is:

```bash
python examples/runtime_tensor_store_evidence.py
```

The CI-facing composition point is:

```bash
python examples/runtime_evidence_gate.py
```

Its golden evidence is:

```text
tests/golden/runtime_tensor_store_evidence/proof_of_execution.json
```

The gate golden is:

```text
tests/golden/proofs/runtime_evidence_gate.txt
```

## Security Boundary

Runtime Tensor Store Evidence is metadata only. It does not include tensor
values, tensor-value digests, host paths, device identifiers, generated code,
plugin entrypoints, commands, environment variables, benchmark samples, or
backend artifacts.

The metadata digest covers record metadata only: tensor name, shape, dtype,
role, read-only status, and raw-value omission status. It never hashes tensor
contents.

## Current Limitations

- The report tracks Runtime Executor v0 only.
- The current runtime value dtype is `float64`.
- The report is not a memory allocator, aliasing model, cache report, device
  placement report, or native-performance artifact.
- Future allocator work should keep using Runtime Allocation Plan and Runtime
  Memory Budget as the memory-planning review surfaces.
