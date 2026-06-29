# RFC 0237: Objective Alpha Kernel Ingress Proof Bundle Catalog Entry

## Status

Accepted.

## Context

Objective Alpha Public Evidence Catalog exists as the digest-only growth surface
after the fixed sixteen-entry Public Proof Bundle reached capacity. The catalog
already binds the governance Extension Policy and the Runtime Backend
Equivalence Portfolio.

The strongest next research connection is not another runtime-only artifact. It
is the bridge from a realistic Source-To-Intent Kernel Ingress proof bundle into
the same public Objective Alpha review surface. That proof bundle already binds
Kernel Ingress, runtime matrix coverage, runtime step trace, evidence-bundle and
output-closure indexes, replay-verifier index, backend equivalence, shape
profiles, coverage policy, backend alignment, boundary budget, rejection
coverage, diagnostics, conformance gate, and idiom alignment by digest.

## Decision

Add `source_to_intent_research_kernel_ingress_proof_bundle` as the first
`frontend_runtime_proof` entry in Objective Alpha Public Evidence Catalog v0.

The public catalog contract remains anchored at:

- example: `examples/objective_alpha_public_evidence_catalog.py`
- schema: `schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json`
- golden: `tests/golden/proofs/objective_alpha_public_evidence_catalog.json`
- docs: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md`

The catalog entry is:

- evidence ID: `source_to_intent_research_kernel_ingress_proof_bundle`
- entry point: `python examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- artifact kind: `schema_versioned_source_to_intent_kernel_ingress_proof_bundle_report`
- extension tier: `frontend_runtime_proof`
- raw output policy: `digest_only`

The catalog stores only the SHA-256 digest of the serialized Kernel Ingress
Proof Bundle report. The proof bundle remains owned by its own schema, golden,
docs, tests, and source-to-intent evidence gates.

## Security Boundary

This catalog entry does not execute the Kernel Ingress example, resolve paths,
access devices, discover plugins, load dynamic libraries, spawn subprocesses,
touch the network, run JIT code, parse source, import Triton modules, or
authorize generated artifacts.

It does not serialize module source, extracted kernel source, Source Intent
payloads, tensor values, runtime handles, host paths, device identifiers,
backend artifacts, raw timing samples, raw benchmark output, or native
performance claims.

## Consequences

Objective Alpha now exposes a small public catalog with one governance entry,
one runtime-proof entry, and one frontend-runtime-proof entry. That makes the
Universal Compute proof surface more balanced: reviewers can inspect both
backend placement equivalence and realistic Source-To-Intent Kernel Ingress
research evidence without expanding the fixed Public Proof Bundle.

Future frontend-runtime catalog entries must follow the same path: existing
schema-versioned source-free evidence first, RFC-bound catalog admission second,
digest-only public linkage always.
