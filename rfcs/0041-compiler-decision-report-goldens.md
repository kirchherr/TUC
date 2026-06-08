# RFC 0041: Compiler Decision Report Goldens

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Gamma/Delta

## Summary

TUC adds golden compiler decision-report fixtures for proof and MVP graphs.

The fixtures live under `tests/golden/compiler_decisions/` and cover:

- `proof_of_abstraction.txt`
- `proof_of_reduction.txt`
- `phase1_mlp_block.txt`

## Motivation

Compiler decision reports connect backend support diagnostics to final runtime
assignments. They are now part of TUC's inspectability contract.

Without golden fixtures, changes to accepted backend candidates, rejected
backend candidates, fallback reasons, or assignment reasons could drift without
the same review pressure already applied to HAC-IR and runtime-plan dumps.

## Decision

Add deterministic text fixtures for representative proof and MVP graphs.

Add `tests/test_compiler_decision_report_golden.py` to compare each fixture
against `CompilationResult.dump_decision_report()`.

## Security Model

The tests build fixed in-repository typed graphs and trusted in-memory
capability data.

They do not:

- discover backend plugins
- import user-controlled modules
- execute backend code
- spawn subprocesses
- load dynamic libraries
- access devices
- execute generated artifacts
- touch the network

Golden files are repository-owned plain text. Updating them should be treated
as a compiler-contract change.

## Consequences

- Backend support evidence becomes reviewable as stable text.
- Fallback behavior is now golden-tested next to accepted/rejected capability
  reasoning.
- Future candidate scoring has a stable baseline to preserve or intentionally
  update.

## Follow-Up

1. Add golden decision reports for future softmax proof graphs.
2. Add candidate-score fields only after scoring is documented and stable.
3. Keep decision-report details bounded and free of host paths or executable
   backend details.
