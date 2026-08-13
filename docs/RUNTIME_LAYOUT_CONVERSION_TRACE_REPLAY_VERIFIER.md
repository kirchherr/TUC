# Runtime Layout Conversion Trace Replay Verifier v0

Runtime Layout Conversion Trace Replay Verifier v0 checks serialized Runtime
Layout Conversion Evidence and Runtime Layout Conversion Trace Index reports by
metadata digest.

It does not rerun the runtime, execute converters, load backend artifacts,
access devices, inspect file paths, or deserialize tensor values.

## Contract

- Schema:
  `schemas/runtime_layout_conversion_trace_replay_verifier_report.v0.schema.json`
- Example: `examples/runtime_layout_conversion_trace_replay_verifier.py`
- Golden:
  `tests/golden/runtime_layout_conversion_trace_replay_verifier/current_report.json`
- Contract: `runtime_layout_conversion_trace_replay_verifier.review.v0`
- Replay mode: `metadata_digest_replay_only`
- Input policy: `serialized_json_reports_only`
- Re-execution policy: `runtime_reexecution_not_required`
- Required inputs:
  `runtime_layout_conversion_evidence`,
  `runtime_layout_conversion_trace_index`

## What It Checks

The verifier accepts only serialized JSON reports and checks:

- graph-name equality between evidence and trace index;
- Trace Index `source_layout_conversion_evidence_digest` against the serialized
  Evidence report digest;
- Trace Index `source_partition_plan_digest` against the Evidence
  `source_partition_plan_digest`;
- conversion-count equality;
- a replayed conversion-metadata digest projected from Trace Index records
  against the Evidence `conversion_metadata_digest`;
- the `conversion_not_materialized_as_runtime_step` materialization policy.

## Why It Exists

Runtime Evidence Gate already checks the live report objects during a gate
invocation. This verifier makes the same layout-conversion trace boundary
reviewable from serialized metadata, just like Runtime Evidence Replay Verifier
does for execution bundle and output closure evidence.

The next consumer is Runtime Backend Equivalence Layout Binding, which binds
this verifier to the mixed Backend Equivalence report by metadata digest. See
[RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING.md](RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING.md).

## Security Boundary

The verifier must not accept source text, raw tensor values, tensor-value
digests, runtime handles, allocation handles, memory addresses, device
identifiers, host paths, command lines, generated code, backend artifacts,
plugin entrypoints, dynamic libraries, benchmark samples, or executable
surfaces.

It fails closed on malformed JSON, unexpected contracts, forged digests,
conversion-record drift, graph drift, policy drift, and forbidden input
fragments.
