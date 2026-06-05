# Roadmap Status

This file tracks concrete progress against the roadmap. It is deliberately
shorter and more operational than `ROADMAP.md`.

## Completed

### Phase 0: Project Foundation

- Open-source repository structure.
- Docker development environment.
- Governance, contribution, security, issue, PR, and RFC scaffolding.
- Initial Python package under `src/tuc`.
- Prototype backend capability model.
- Linear algebra simulator backend.
- Rule-based runtime partitioning.
- Unit tests and Phase 0 vertical-slice example.
- Initial commit pushed to GitHub.

## In Progress

### Phase 1: Triton Compatibility And IR Skeleton

Current slice:

- Explicit `tlir`, `hac-ir`, and `hs-ir` module stages.
- TLIR -> HAC-IR lowering.
- HAC-IR -> HS-IR lowering with backend assignments.
- Stable text dumps for debugging and tests.
- Phase 1 vertical-slice example.
- MVP kernel family definition.
- Triton compatibility matrix.
- Data-movement-aware HAC-IR annotations for MVP kernels.
- HS-IR movement summaries for future runtime planning.
- Secure IR validation and immutable metadata baseline.
- Backend capability validation and memory-domain metadata.
- Transfer-byte-aware partition plan diagnostics.
- Apache-2.0 license and initial supply-chain security workflows.
- Explicit runtime transfer-edge objects.
- Runtime layout-conversion costing.
- Backend layout capability schema.
- Runtime transfer bandwidth, latency, and energy estimates.
- Stable runtime plan dump.
- Backend produced-layout schema.
- Validated in-memory transfer-cost profiles.
- Runtime plan golden dumps.
- Schema-versioned backend manifest files.
- Calibrated transfer-cost profile files.
- Golden-kernel correctness suite.
- Prototype frontend adapter for Triton-like kernel metadata.
- Baseline benchmark harness that can run with or without CUDA.
- First native MLIR design spike.
- HAC-IR v0 dialect contracts for MVP operations and compiler attributes.
- HS-IR v0 contracts for backend assignments, produced layouts, and runtime-transfer summaries.
- Backend API v0.1 authoring guide for external prototype backends.

## Next

- Minimal backend author certification checklist and negative-test template.
- Branch protection and required CI/security checks on `main`.
- Release provenance, SBOM, and signed artifacts before first package release.
