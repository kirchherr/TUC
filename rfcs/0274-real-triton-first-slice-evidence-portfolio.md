# RFC 0274: Real Triton First Slice Evidence Portfolio

## Status

Accepted.

## Context

TUC now has several separate but related reports for the first Real Triton
research direction:

- first-slice prerequisite planning;
- maintainer security review packet;
- missing maintainer approval artifact;
- fail-closed source-ingestion admission gate;
- pre-claim evidence graph acyclicity;
- first real Triton kernel path;
- project-level research scope claim gate.

Each artifact is useful on its own, but reviewers need one compact milestone
that shows both sides of the current proof:

```text
bounded realistic Triton-shaped path: PASS
direct source-ingestion admission: BLOCKED
```

## Decision

Add a digest-only, source-free Real Triton First Slice Evidence Portfolio report.

The portfolio binds:

- `real_triton_first_admissible_slice_plan`
- `source_ingestion_maintainer_security_review_packet`
- `source_ingestion_maintainer_approval_artifact`
- `source_ingestion_admission_gate`
- `source_ingestion_preclaim_evidence_graph_acyclicity_gate`
- `first_real_triton_kernel_path`
- `research_scope_claim_gate`

The portfolio status is `PASS` only when the bounded first real path passes and
the source-ingestion admission boundary remains closed.

## Non-Goals

This RFC does not:

- admit direct Triton source ingestion;
- implement or approve a production source parser;
- execute Triton JIT;
- import frontend packages;
- discover plugins;
- access devices;
- execute generated artifacts;
- execute native backends;
- claim native performance parity;
- claim CUDA, ROCm, XLA, TVM, or IREE replacement.

## Security Model

The portfolio is metadata-only. It stores evidence IDs, contracts, statuses,
source-free flags, and SHA-256 digests.

It must reject reports that add raw source, Source Intent payload bodies, raw
tensor values, runtime handles, device IDs, host paths, commands, generated
code, backend artifacts, or plugin entrypoints.

## Acceptance Criteria

- Add `examples/real_triton_first_slice_evidence_portfolio.py`.
- Add
  `schemas/real_triton_first_slice_evidence_portfolio_report.v0.schema.json`.
- Add deterministic golden evidence at
  `tests/golden/frontend/real_triton_first_slice_evidence_portfolio_report.json`.
- Add tests for contract shape, golden stability, example execution, fail-closed
  drift rejection, source-free output, schema shape, documentation, and CI
  binding.
- Add a CI example step.
- Document the portfolio at
  `docs/REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO.md`.

## Consequences

Reviewers now get a single milestone artifact for the first Real Triton research
slice without weakening TUC's secure-by-design boundary. The portfolio makes the
project easier to understand while preserving the separation between research
evidence and source-ingestion admission.
