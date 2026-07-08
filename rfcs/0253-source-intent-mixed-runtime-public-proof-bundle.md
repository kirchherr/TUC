# RFC 0253: Source Intent Mixed Runtime Public Proof Bundle

## Status

Accepted

## Context

TUC needs practical proof steps that keep the research goal centered:
hardware-independent compute intent should be executable through trusted
prototype placements and reviewable through bounded evidence.

Existing evidence already covers Source Intent runtime returns, Runtime Public
Output Bundle, Reference Correctness, and Runtime Backend Equivalence. The next
useful step is a single digest-only proof bundle that starts at Source Intent
plain data and ends at a mixed `systolic-sim + vector-sim` placement checked
against a neutral `reference-cpu` baseline.

## Decision

Add a Source Intent Mixed Runtime Public Proof Bundle at:

```text
examples/source_intent_mixed_runtime_public_proof_bundle.py
docs/SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE.md
schemas/source_intent_mixed_runtime_public_proof_bundle_report.v0.schema.json
tests/golden/frontend/source_intent_mixed_runtime_public_proof_bundle.json
```

The proof bundle uses this path:

```text
Source Intent plain data
  -> Source Intent metadata conversion
  -> ComputeGraph / HAC-IR
  -> reference-cpu baseline execution
  -> systolic-sim + vector-sim candidate execution
  -> Runtime Output Contract
  -> Runtime Public Output Bundle
  -> Runtime Reference Correctness
  -> Runtime Backend Equivalence
  -> digest-only public proof bundle
```

The accepted candidate backend sequence is:

```text
systolic-sim -> vector-sim -> vector-sim -> vector-sim
```

## Acceptance Criteria

- The example emits schema-versioned JSON with contract
  `source_intent_mixed_runtime_public_proof_bundle.e2e.v0`.
- The report binds Source Intent, metadata conversion, readiness, execution
  trace, output manifest, output contract, public output bundle, reference
  correctness, and backend equivalence artifacts by SHA-256 digest.
- The serialized report contains no raw tensor values, value digests, runtime
  handles, device IDs, host paths, commands, generated code, backend artifacts,
  raw source text, or Source Intent payload bodies.
- The report is covered by deterministic golden tests.
- CI runs `examples/source_intent_mixed_runtime_public_proof_bundle.py`.

## Non-Goals

- No production Triton parser.
- No `@triton.jit` execution.
- No native backend execution.
- No device allocation or runtime handle serialization.
- No native performance claim.

## Security Considerations

This RFC keeps Source Intent as data and runtime execution inside the fixed
trusted executor registry. It does not add plugin discovery, dynamic imports,
device access, subprocesses, generated artifact execution, or network access.
All public evidence remains digest-only and fail-closed under the JSON schema.
