# RFC 0226: Objective Alpha Transfer Evidence Entries

Status: Accepted

## Summary

Add Runtime Transfer Trace Index, Runtime Transfer Trace Replay Verifier, and
Runtime Backend Equivalence Transfer Binding as fixed digest-only entries in the
Objective Alpha Public Proof Bundle.

## Motivation

Runtime Evidence Gate now requires the systolic backend-equivalence proof slice
to carry transfer trace index, verified transfer trace replay, and
backend-equivalence/transfer binding evidence. Reviewers should be able to see
those proof boundaries from the public Objective Alpha entry point without
unpacking the gate output.

## Decision

Add these entries to Objective Alpha Public Proof Bundle v0:

- Evidence ID: `runtime_transfer_trace_index`
- Entry point: `python examples/runtime_transfer_trace_index.py`
- Artifact kind: `schema_versioned_transfer_trace_index_report`

- Evidence ID: `runtime_transfer_trace_replay_verifier`
- Entry point: `python examples/runtime_transfer_trace_replay_verifier.py`
- Artifact kind: `schema_versioned_transfer_trace_replay_verifier_report`

- Evidence ID: `runtime_backend_equivalence_transfer_binding`
- Entry point: `python examples/runtime_backend_equivalence_transfer_binding.py`
- Artifact kind: `schema_versioned_backend_equivalence_transfer_binding_report`

Update the bundle model, schema, golden fixture, tests, docs, and roadmap status
in the same change.

## Security

The new entries are digest-only references to fixed in-repository evidence
builders. The bundle still rejects raw output embedding, source text, host paths,
backend artifacts, generated code, device identifiers, plugin entry points,
subprocess surfaces, and native performance claims.

## Consequences

Objective Alpha now exposes the transfer-boundary proof chain directly:
Runtime Backend Equivalence, Runtime Transfer Trace Index, Runtime Transfer
Trace Replay Verifier, and Runtime Backend Equivalence Transfer Binding remain
gate-bound while also becoming reviewer-visible public bundle entries.