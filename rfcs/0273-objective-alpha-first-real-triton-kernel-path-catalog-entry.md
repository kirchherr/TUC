# RFC 0273: Objective Alpha First Real Triton Kernel Path Catalog Entry

## Status

Accepted.

## Context

RFC 0272 added the First Real Triton Kernel Path as a compact, source-free proof
for the bounded `research_module_mvp_pipeline` / `mvp_pipeline` path. That proof
is important enough to be visible from Objective Alpha's public evidence index,
but it must not reopen the fixed sixteen-entry Public Proof Bundle.

Objective Alpha already uses the Public Evidence Catalog as the append-only,
RFC-bound growth surface for evidence beyond the fixed bundle. The correct
integration point is therefore a catalog entry, not a bundle mutation.

## Decision

Add `first_real_triton_kernel_path` as the sixth Objective Alpha Public Evidence
Catalog entry.

The entry binds:

- evidence ID: `first_real_triton_kernel_path`
- entry point: `python examples/first_real_triton_kernel_path.py`
- artifact kind: `schema_versioned_first_real_triton_kernel_path_report`
- extension tier: `frontend_runtime_proof`
- digest source: `first_real_triton_kernel_path_report`
- raw output policy: `digest_only`

The catalog report and catalog admission gate must expose the proof only through
SHA-256 metadata digests and fixed catalog metadata. The Objective Alpha research
claim count becomes 16 fixed public-bundle entries plus 6 catalog entries, for
22 public evidence entries.

## Security Boundary

This RFC does not authorize broad source parsing, frontend package import,
Triton JIT execution, device access, dynamic library loading, plugin discovery,
subprocess execution, generated artifact execution, native backend execution, or
native performance claims.

The catalog entry must not serialize raw source, Source Intent payload bodies,
tensor values, runtime handles, device identifiers, host paths, backend
artifacts, commands, raw timing samples, or raw benchmark output.

## Acceptance Criteria

- The catalog contains six fixed entries in append-only order.
- The sixth entry is `first_real_triton_kernel_path`.
- The catalog and admission gate bind the First Real Triton Kernel Path report by
  SHA-256 metadata digest.
- The Objective Alpha research claim and gate report public evidence count 22.
- Existing blocked claims and blocked execution surfaces remain unchanged.

## Artifacts

- Catalog doc: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md`
- Catalog example: `examples/objective_alpha_public_evidence_catalog.py`
- Catalog schema: `schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json`
- Catalog golden: `tests/golden/proofs/objective_alpha_public_evidence_catalog.json`
- Gate doc: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md`
- Gate example: `examples/objective_alpha_public_evidence_catalog_admission_gate.py`
- Gate schema: `schemas/objective_alpha_public_evidence_catalog_admission_gate_report.v0.schema.json`
- Gate golden: `tests/golden/proofs/objective_alpha_public_evidence_catalog_admission_gate.json`
- First-path proof: `examples/first_real_triton_kernel_path.py`
- First-path proof RFC: `rfcs/0272-first-real-triton-kernel-path.md`
- RFC path: `rfcs/0273-objective-alpha-first-real-triton-kernel-path-catalog-entry.md`
