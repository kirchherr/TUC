# Phase 0 Plan

Phase 0 turns the TUC concept into a project that can be built, tested,
reviewed, and extended.

## Goals

- Establish a serious open-source repository structure.
- Build a reproducible Docker development environment.
- Define the first hardware-agnostic IR concepts.
- Define the first backend capability model.
- Create a tiny simulator backend.
- Create a simple runtime partitioning path.
- Add tests, examples, CI, docs, RFCs, and governance.

## Deliverables

- `src/tuc`: Python package for the prototype.
- `tests`: Unit tests for Phase 0 behavior.
- `examples`: Runnable vertical-slice examples.
- `docs`: Architecture and development docs.
- `rfcs`: Design proposals and accepted decisions.
- `.github`: Issue templates, PR template, and CI workflow.

## Open Decisions

- Final open-source license.
- Whether the native compiler starts as a Triton fork, an extension layer, or a
  parallel prototype.
- First real MLIR dialect implementation strategy.
- First partner-facing backend API shape.
- First benchmark suite.

## Exit Criteria

Phase 0 is complete when:

- CI passes.
- The Docker environment is reproducible.
- The Phase 0 vertical slice runs.
- The first architecture RFC is accepted.
- The license decision is resolved.
- The first MLIR implementation task is ready to start.
