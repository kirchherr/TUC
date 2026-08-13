# RFC 0150: Runtime Mixed Tensor Store Evidence

## Status

Accepted.

## Context

Runtime Mixed Backend Equivalence proves that a `reference-cpu` baseline and an
accepted `systolic-sim -> vector-sim -> vector-sim -> vector-sim` candidate
preserve terminal output semantics for one heterogeneous graph.

That is necessary but not sufficient for the practical proof trail. The mixed
slice also needs to show that Runtime Executor value records carry the accepted
placement metadata for each internal tensor without exposing raw tensor values.

## Decision

Add `examples/runtime_mixed_tensor_store_evidence.py` and the deterministic
golden:

```text
tests/golden/runtime_tensor_store_evidence/runtime_mixed_backend_equivalence.json
```

The report reuses the existing Runtime Tensor Store Evidence contract and checks
the candidate mixed accelerator `PartitionPlan` against the observed
`RuntimeValueRecord` metadata.

## Security Boundary

This change does not add parser behavior, plugin discovery, dynamic imports,
device access, native execution, JIT execution, generated artifact execution,
filesystem path resolution, network access, subprocess execution, raw tensor
serialization, runtime handles, raw timing samples, or benchmark output.

It executes only the existing trusted in-process prototype runtime and serializes
bounded metadata: tensor names, shapes, dtype, producer provenance, planned
backend, memory domain, layout, placement source, read-only status, and
raw-value omission status.

## Consequences

The mixed accelerator slice now has two complementary runtime evidence views:
backend equivalence for terminal output semantics and tensor-store evidence for
internal value-record placement metadata. Future mixed placement changes must
update the executable example, golden report, tests, and roadmap documentation
together.
