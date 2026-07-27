# Real Triton First Slice Evidence Portfolio

Real Triton First Slice Evidence Portfolio v0 is the reviewer-facing milestone
that binds the current first Real Triton research path and its safety boundary
into one digest-only report.

It answers one question:

```text
Can TUC show a realistic Triton-shaped MVP kernel path and the admission
boundary around future source ingestion without turning that boundary into an
open compiler surface?
```

Current answer: `PASS` for the bounded research portfolio, with source
ingestion still blocked.

## Contract

- Portfolio contract:
  `real_triton_first_slice_evidence_portfolio.research_boundary.v0`
- Report schema:
  `schemas/real_triton_first_slice_evidence_portfolio_report.v0.schema.json`
- Example:
  `examples/real_triton_first_slice_evidence_portfolio.py`
- Golden:
  `tests/golden/frontend/real_triton_first_slice_evidence_portfolio_report.json`
- Tests:
  `tests/test_real_triton_first_slice_evidence_portfolio.py`
- RFC:
  `rfcs/0274-real-triton-first-slice-evidence-portfolio.md`
- CI entry: `.github/workflows/ci.yml`

## Bound Evidence

The portfolio binds these reports by SHA-256 digest:

- `examples/real_triton_first_slice_plan.py`
- `examples/source_ingestion_maintainer_security_review_packet.py`
- `examples/source_ingestion_maintainer_approval_artifact.py`
- `examples/source_ingestion_admission_gate.py`
- `examples/source_ingestion_preclaim_acyclicity_gate.py`
- `examples/first_real_triton_kernel_path.py`
- `examples/research_scope_claim_gate.py`

This keeps the first-slice prerequisite plan, maintainer review packet, missing
approval artifact, fail-closed admission gate, pre-claim acyclicity gate, first
real Triton kernel path proof, and project-level research-scope boundary visible
in one stable artifact.

## What It Proves

- the bounded `mvp_pipeline` first real Triton-shaped kernel path is `PASS`;
- Source Intent re-intake reaches trusted runtime evidence;
- backend-equivalence evidence is bound as metadata;
- first-slice prerequisite evidence is reviewable;
- source-ingestion admission remains fail-closed;
- the project claim remains a research proof, not a production compiler claim.

## What Stays Blocked

The portfolio explicitly keeps these claims false:

- arbitrary Triton source ingestion;
- production source parsing;
- source-to-ComputeGraph admission;
- native backend execution;
- native performance parity;
- CUDA replacement;
- runtime-handle residency.

It also records `admitted = false`, `direct_source_ingestion = false`,
`external_approval_present = false`, `surface_opened = false`,
`triton_jit_execution = false`, `device_access = false`, and
`generated_artifact_execution = false`.

## Security Boundary

The portfolio validates already-produced metadata. It does not parse source,
import frontend packages, discover plugins, run Triton JIT, access devices,
execute generated artifacts, execute native backends, serialize tensor values,
or serialize runtime handles.

All bound artifacts are represented by IDs, contracts, statuses, source-free
flags, and SHA-256 digests. The report is intentionally source-free and
metadata-only.
