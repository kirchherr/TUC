# Runtime Transfer Evidence

Runtime Transfer Evidence v0 records planned cross-domain transfer edges from
an accepted `PartitionPlan` as data-only review evidence.

It answers one narrow question:

```text
Which tensors must move between runtime memory domains according to the plan,
and what deterministic planning-cost estimate was attached?
```

## Contract

- Report schema: `schemas/runtime_transfer_evidence_report.v0.schema.json`
- Report schema version: `tuc.runtime_transfer_evidence_report.v0`
- Evidence contract: `runtime_transfer_evidence.data_only.v0`
- Transfer scope: `planned_logical_transfer_only`
- Execution policy: `does_not_execute_transfers`
- Residency claim: `not_physical_residency_evidence`
- Cost claim: `planning_estimate_not_measurement`
- Raw value policy: `omitted_by_policy`

## Evidence

The canonical example is:

```bash
python examples/runtime_transfer_evidence.py
python examples/runtime_transfer_trace_index.py
python examples/runtime_transfer_trace_replay_verifier.py
```

The deterministic golden reports are:

```text
tests/golden/runtime_transfer_evidence/current_report.json
tests/golden/runtime_transfer_trace_index/current_report.json
tests/golden/runtime_transfer_trace_replay_verifier/current_report.json
```

The current proof slice records the planned `device_sram -> host_ram` transfer
from the systolic backend-equivalence candidate without serializing tensor
values or runtime handles.

[Runtime Transfer Trace Index](RUNTIME_TRANSFER_TRACE_INDEX.md) binds the same
planned transfer evidence to concrete producer and consumer
`RuntimeExecutionTrace` steps, with schema
`schemas/runtime_transfer_trace_index_report.v0.schema.json`, while preserving
the `transfer_not_materialized_as_runtime_step` boundary. Runtime Evidence
Matrix and Runtime Evidence Gate require that index as
`runtime_transfer_trace_index_systolic` for the systolic backend-equivalence
proof slice.

[Runtime Transfer Trace Replay Verifier](RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER.md)
checks serialized Transfer Evidence and Transfer Trace Index reports by metadata
digest, with schema `schemas/runtime_transfer_trace_replay_verifier_report.v0.schema.json`,
while preserving the same no-transfer-execution and metadata-only boundary.

## Security Boundary

The report is built from already accepted graph and `PartitionPlan` data. It
does not execute transfers, discover plugins, access devices, materialize
memory pools, inspect host paths, spawn subprocesses, run JIT code, or serialize
raw tensor values.

Transfer latency and energy fields are deterministic planning estimates. They
are not hardware measurements and must not be used as native performance
evidence.
