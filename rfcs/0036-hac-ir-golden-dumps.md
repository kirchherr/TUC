# RFC 0036: HAC-IR Golden Dumps

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Beta

## Summary

TUC adds deterministic HAC-IR golden dump fixtures for the Objective Alpha
proof graph and the Phase 1 MVP graph.

## Motivation

The Universal Compute claim depends on HAC-IR staying stable, inspectable, and
hardware-independent. The proof report already includes HAC-IR, and runtime
plans already have narrower golden fixtures. HAC-IR itself now needs the same
reviewable contract so maintainers can see when compiler-produced facts,
planning constraints, or operation spellings change.

## Decision

Add static fixtures under `tests/golden/hac_ir/` and compare them against
`CompilationResult.dump(IRStage.HAC_IR)`.

The initial fixture set covers:

- `proof_of_abstraction.txt`: the Objective Alpha proof graph.
- `phase1_mlp_block.txt`: the Phase 1 MVP graph used by the IR pipeline
  example.

The test compiles fixed in-repository typed graph builders with trusted
in-memory backend capability data. It does not execute example scripts through
subprocesses.

## Security Model

HAC-IR golden tests must remain pure contract checks:

- No backend plugin discovery.
- No dynamic imports of user-controlled modules.
- No subprocesses.
- No device access.
- No generated-artifact execution.
- No network access.

The fixtures are repository-owned plain text. Updating them is a visible
compiler-contract change and should be reviewed through the HAC-IR semantic
charter and neutrality checklist.

## Consequences

- HAC-IR dump changes for proof and MVP graphs require intentional fixture
  updates.
- Reviewers can diff compiler facts such as movement summaries, layouts,
  arithmetic intensity, and accepted planning constraints.
- Future native MLIR work has a concrete Python-level artifact to preserve or
  intentionally migrate.

## Follow-Up

1. Add HAC-IR golden fixtures for the second proof graph once reduction or
   softmax is added.
2. Add frontend-adapter-generated HAC-IR fixtures after the ingestion boundary
   has its own reviewer checklist.
3. Mirror the fixture policy in future native MLIR serialization tests.
