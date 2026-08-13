# Runtime Transfer Trace Replay Verifier v0

Runtime Transfer Trace Replay Verifier v0 checks serialized Runtime Transfer
Evidence and Runtime Transfer Trace Index reports by metadata digest.

It does not rerun the runtime, execute transfers, load backend artifacts,
access devices, inspect file paths, or deserialize tensor values.

## Contract

- Schema:
  `schemas/runtime_transfer_trace_replay_verifier_report.v0.schema.json`
- Example: `examples/runtime_transfer_trace_replay_verifier.py`
- Golden:
  `tests/golden/runtime_transfer_trace_replay_verifier/current_report.json`
- Contract: `runtime_transfer_trace_replay_verifier.review.v0`
- Replay mode: `metadata_digest_replay_only`
- Input policy: `serialized_json_reports_only`
- Re-execution policy: `runtime_reexecution_not_required`
- Required inputs:
  `runtime_transfer_evidence`,
  `runtime_transfer_trace_index`

## What It Checks

The verifier accepts only serialized JSON reports and checks:

- graph-name equality between evidence and trace index;
- Trace Index `source_transfer_evidence_digest` against the serialized Evidence
  report digest;
- Trace Index `source_partition_plan_digest` against the Evidence
  `source_partition_plan_digest`;
- transfer-count equality;
- a replayed transfer-metadata digest projected from Trace Index records
  against the Evidence `transfer_metadata_digest`;
- the `transfer_not_materialized_as_runtime_step` materialization policy.

## Why It Exists

Runtime Transfer Evidence records planned logical movement. Runtime Transfer
Trace Index aligns that planned movement to producer and consumer execution
steps. This verifier makes the boundary reviewable from serialized metadata,
so transfer evidence and trace evidence cannot drift apart without producing a
failed replay report.

This is still not physical transfer execution, device-residency evidence, or a
performance claim. It is a digest-bound review check for the planned transfer
trace boundary.

The next consumer is Runtime Backend Equivalence Transfer Binding, which binds
this verifier to the systolic Backend Equivalence report by metadata digest. See
[RUNTIME_BACKEND_EQUIVALENCE_TRANSFER_BINDING.md](RUNTIME_BACKEND_EQUIVALENCE_TRANSFER_BINDING.md).

## Security Boundary

The verifier must not accept source text, raw tensor values, tensor-value
digests, runtime handles, allocation handles, memory addresses, device
identifiers, host paths, command lines, generated code, backend artifacts,
plugin entrypoints, dynamic libraries, benchmark samples, or executable
surfaces.

It fails closed on malformed JSON, unexpected contracts, forged digests,
transfer-record drift, graph drift, policy drift, and forbidden input
fragments.