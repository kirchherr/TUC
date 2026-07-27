# RFC 0275: Objective Alpha Real Triton First Slice Portfolio Catalog Entry

## Status

Accepted.

## Context

RFC 0274 added the Real Triton First Slice Evidence Portfolio as a digest-only,
source-free milestone for the bounded first Real Triton research slice and its
closed source-ingestion boundary. That portfolio is important enough to be
visible from Objective Alpha's public evidence index, but it must not reopen the
fixed sixteen-entry Public Proof Bundle.

The portfolio must also stay below Objective Alpha claim gates in the Evidence
DAG. It therefore binds first-slice prerequisite evidence, the fail-closed
source-ingestion boundary, pre-claim acyclicity, and First Real Triton Kernel
Path evidence, while leaving project-level claim gates above the catalog.

## Decision

Add `real_triton_first_slice_evidence_portfolio` as the seventh Objective Alpha
Public Evidence Catalog entry.

The entry binds:

- evidence ID: `real_triton_first_slice_evidence_portfolio`
- entry point: `python examples/real_triton_first_slice_evidence_portfolio.py`
- artifact kind: `schema_versioned_real_triton_first_slice_evidence_portfolio_report`
- extension tier: `frontend_runtime_proof`
- digest source: `real_triton_first_slice_evidence_portfolio_report`
- raw output policy: `digest_only`

The catalog report and catalog admission gate expose the portfolio only through
SHA-256 metadata digests and fixed catalog metadata. The Objective Alpha research
claim count becomes 16 fixed public-bundle entries plus 7 catalog entries, for
23 public evidence entries.

## Security Boundary

This RFC does not authorize broad source parsing, frontend package import,
Triton JIT execution, device access, dynamic library loading, plugin discovery,
subprocess execution, generated artifact execution, native backend execution, or
native performance claims.

The catalog entry must not serialize raw source, Source Intent payload bodies,
tensor values, runtime handles, device identifiers, host paths, backend
artifacts, commands, raw timing samples, raw benchmark output, or generated code.

## Acceptance Criteria

- The catalog contains seven fixed entries in append-only order.
- The seventh entry is `real_triton_first_slice_evidence_portfolio`.
- The catalog and admission gate bind the portfolio report by SHA-256 metadata
  digest.
- The portfolio remains below project-level claim gates and does not create an
  Objective Alpha catalog or research-claim dependency cycle.
- The Objective Alpha research claim and gate report public evidence count 23.
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
- Portfolio proof: `examples/real_triton_first_slice_evidence_portfolio.py`
- Portfolio proof RFC: `rfcs/0274-real-triton-first-slice-evidence-portfolio.md`
- RFC path: `rfcs/0275-objective-alpha-real-triton-first-slice-portfolio-catalog-entry.md`