# RFC 0200: Objective Alpha Public Proof Bundle

Status: Accepted

## Summary

Add a digest-only public proof bundle for Objective Alpha. The bundle connects
proof execution, runtime evidence matrix, runtime evidence gate, and research
onboarding evidence into one deterministic JSON artifact.

## Motivation

The roadmap now asks for the first public proof path to stay short and
reviewable. The onboarding evidence explains how to start. This bundle answers
which current proof artifacts are bound together for Objective Alpha without
copying large proof outputs into top-level documentation.

## Design

Add:

- `src/tuc/objective_alpha.py` for the bundle model;
- `examples/objective_alpha_public_proof_bundle.py` for deterministic emission;
- `schemas/objective_alpha_public_proof_bundle.v0.schema.json` for fail-closed shape;
- `docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE.md` for the review contract;
- `tests/golden/proofs/objective_alpha_public_proof_bundle.json` for stable evidence;
- `tests/test_objective_alpha_public_proof_bundle.py` for contract, schema,
  and non-claim checks.

## Security

The bundle is digest-only. It does not accept external inputs, parse source,
discover plugins, access devices, ingest benchmark output, load dynamic
libraries, execute generated artifacts, or publish raw tensor values.

The example runs trusted in-repository evidence builders and records only
SHA-256 digests plus fixed entry point metadata.

## Consequences

Objective Alpha now has a single public proof bundle for reviewer orientation.
Future changes to the first public proof path must update the bundle, schema,
golden, tests, documentation, and roadmap status together.
