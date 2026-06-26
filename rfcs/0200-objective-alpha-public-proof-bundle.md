# RFC 0200: Objective Alpha Public Proof Bundle

Status: Accepted

## Summary

Add a digest-only public proof bundle for Objective Alpha. The bundle connects
proof execution, runtime evidence matrix, runtime evidence gate, Proof Of
Backend Equivalence, Runtime Execution Output Closure, transfer-boundary trace
index, replay, and binding, layout-transition trace index, replay, and binding,
allocation reconciliation, Runtime Memory Planning Gate evidence, research
onboarding evidence, Source-To-Intent Research Proof Bundle evidence, and Kernel
Ingress Evidence Gate evidence into one deterministic JSON artifact.

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

The example runs trusted in-repository evidence builders, including Proof Of
Backend Equivalence, Runtime Execution Output Closure, transfer trace index,
replay, and binding, layout trace index, replay, and binding, allocation
reconciliation, Runtime Memory Planning Gate, Source-To-Intent Research Proof
Bundle, and Kernel Ingress Evidence Gate, and records only SHA-256 digests,
fixed entry point metadata, and fixed entry capacity metadata.

## Consequences

Objective Alpha now has a single public proof bundle for reviewer orientation.
Future changes to the first public proof path must update the bundle, schema,
golden, tests, documentation, roadmap status, and the separate
`examples/objective_alpha_public_proof_bundle_gate.py` review gate together.
