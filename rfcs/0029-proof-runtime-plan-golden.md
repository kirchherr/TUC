# RFC 0029: Proof Runtime Plan Golden

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Alpha / Delta

## Summary

TUC adds a dedicated golden runtime-plan artifact for the proof-of-abstraction
graph.

The full proof report is already golden-tested. This RFC adds a narrower
contract for runtime placement and transfer reasoning:

```text
tests/golden/runtime_plans/proof_of_abstraction.txt
```

## Motivation

The masterplan-aligned roadmap makes runtime planning a strategic asset. The
proof-of-abstraction report proves the end-to-end claim, but reviewers also
need a focused way to see whether operation placement and transfer accounting
changed.

A dedicated runtime-plan golden file makes that part of the proof easier to
review and protects against accidental changes to assignment reasons, memory
domains, transfer bytes, latency estimates, or energy estimates.

## Decision

Update `tests/test_runtime_plan_golden.py` to include the proof-of-abstraction
runtime plan built from `examples.proof_of_abstraction.run_proof`.

Add:

- `tests/golden/runtime_plans/proof_of_abstraction.txt`
- Documentation in `docs/PROOF_OF_ABSTRACTION.md`
- Roadmap-status updates for the Phase Alpha / Phase Delta contract

## Security Model

The golden runtime-plan test uses only in-repository proof graph construction,
pure backend capability data, deterministic lowering, and deterministic runtime
planning.

It does not add:

- plugin discovery
- backend dynamic imports
- subprocess backend probing
- dynamic library loading
- device access
- generated-artifact execution

## Consequences

- Runtime planning becomes a first-class proof artifact.
- Placement and transfer reasoning can be reviewed separately from the full
  proof report.
- Future proof graphs should add their own runtime-plan golden dumps before
  claiming reproducibility.
