# RFC 0277: Real Triton First Slice Admission Readiness Gate

- Status: Accepted
- Date: 2026-07-28
- Related:
  - `rfcs/0257-real-triton-first-slice-plan.md`
  - `rfcs/0265-source-ingestion-maintainer-security-review-packet.md`
  - `rfcs/0266-source-ingestion-admission-gate.md`
  - `rfcs/0274-real-triton-first-slice-evidence-portfolio.md`
  - `rfcs/0276-objective-alpha-catalog-acyclicity-gate.md`

## Context

The Real Triton first-slice path now has separate evidence for the plan,
maintainer review packet, missing approval artifact, fail-closed admission gate,
first real Triton kernel path, evidence portfolio, and public catalog
acyclicity. Reviewers still need one compact gate that answers: is this slice
ready to admit source ingestion?

The current answer must remain no. The remaining external evidence is
maintainer security review approval.

## Decision

Add `examples/real_triton_first_slice_admission_readiness_gate.py` as a
source-free, data-only readiness gate. The gate scans fixed Golden evidence
artifacts, binds each by SHA-256 digest, verifies their expected status, and
emits an intentionally blocked readiness report with `gate_passed = false`,
`admission_ready = false`, `admitted = false`, and `surface_opened = false`.

The report is schema-versioned at
`schemas/real_triton_first_slice_admission_readiness_gate_report.v0.schema.json`,
has golden evidence at
`tests/golden/frontend/real_triton_first_slice_admission_readiness_gate_report.json`,
and is documented at `docs/REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE.md`.

## Required Invariants

- first-slice plan evidence is bound;
- maintainer review packet is ready;
- external approval artifact is absent;
- source-ingestion admission gate remains fail-closed;
- first real Triton kernel path has passed;
- first-slice evidence portfolio has passed;
- Objective Alpha catalog acyclicity has passed;
- direct source ingestion remains false;
- source-to-ComputeGraph, source-to-HAC-IR, and source-to-runtime-plan remain false;
- no new execution surface opens;
- evidence remains digest-only and source-free.

## Security Boundary

The gate must not execute source, import frontend packages, discover plugins,
run Triton JIT, access devices, load dynamic libraries, spawn subprocesses,
touch the network, emit generated artifacts, or authorize source-to-IR/runtime
shortcuts. It must not serialize report bodies, source text, Source Intent
payloads, raw tensor values, runtime handles, host paths, device identifiers,
backend artifacts, raw benchmark data, or generated code.

## Consequences

TUC now has a compact readiness answer for the first Real Triton admitting
slice: the repository-side proof chain is bound and reviewable, but admission is
still blocked by the absent external maintainer security review approval.
