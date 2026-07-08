# Source Intent Mixed Runtime Public Proof Bundle

This proof bundle is the smallest current end-to-end TUC path that starts with
Source Intent plain data and ends with reviewable mixed-runtime evidence.

It does not parse Triton or Python source, execute decorators, discover
plugins, touch devices, emit generated code, or claim native performance.

## Claim

```text
Source Intent plain data
  -> execution-free metadata conversion
  -> ComputeGraph / HAC-IR
  -> reference-cpu baseline
  -> systolic-sim + vector-sim candidate placement
  -> trusted Runtime Executor
  -> Output Contract and Public Output Bundle
  -> Reference Correctness
  -> Backend Equivalence
  -> digest-only proof bundle
```

The proof claim is:

```text
source_intent_preserves_public_outputs_across_mixed_backend_placements
```

## Entrypoint

```bash
python examples/source_intent_mixed_runtime_public_proof_bundle.py
```

The report schema is:

```text
schemas/source_intent_mixed_runtime_public_proof_bundle_report.v0.schema.json
```

The deterministic golden evidence is:

```text
tests/golden/frontend/source_intent_mixed_runtime_public_proof_bundle.json
```

## Evidence Bound

The bundle binds these artifacts by SHA-256 digest:

- Source Intent module dump.
- Source Intent metadata conversion report.
- Candidate runtime execution readiness.
- Candidate runtime execution trace.
- Candidate Runtime Output Manifest.
- Candidate Runtime Output Contract.
- Candidate Runtime Public Output Bundle.
- Candidate Runtime Reference Correctness.
- Runtime Backend Equivalence.

The candidate backend sequence is:

```text
systolic-sim -> vector-sim -> vector-sim -> vector-sim
```

The neutral baseline sequence is:

```text
reference-cpu -> reference-cpu -> reference-cpu -> reference-cpu
```

## What It Proves

- Source Intent plain data can describe a mixed-operation MVP pipeline without
  source execution.
- Metadata conversion can produce the graph used for runtime planning.
- A neutral `reference-cpu` baseline and a mixed `systolic-sim + vector-sim`
  placement can preserve the same public terminal output semantics.
- Runtime Output Contract, Public Output Bundle, Reference Correctness, and
  Backend Equivalence can be bound into one digest-only review artifact.

## What It Does Not Prove

- It does not prove broad Triton source parsing.
- It does not prove native GPU, TPU, NPU, systolic hardware, photonic,
  in-memory, analog, or vendor-library execution.
- It does not prove real device residency, allocation handles, stream
  behavior, cache behavior, or physical layout ownership.
- It does not prove native performance parity.

## Security Boundary

The bundle is metadata-only and value-free. Serialized evidence must not
contain raw tensor values, value digests, runtime handles, device IDs, host
paths, commands, generated code, backend artifacts, plugin entrypoints, raw
source text, or Source Intent payload bodies.

The accepted input is Source Intent plain data under
`source_intent_ir.canonical.v0`. This is a research proof surface, not a general
source parser or executable backend admission path.
