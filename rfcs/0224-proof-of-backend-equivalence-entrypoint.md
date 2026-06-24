# RFC 0224: Proof Of Backend Equivalence Entrypoint

- Status: accepted-for-prototype
- Created: 2026-06-24
- Phase: Alpha / Delta

## Summary

Add a canonical proof entrypoint for Backend Equivalence.

This RFC does not add a new runtime executor, execute backend plugins, access
devices, load dynamic libraries, run generated artifacts, serialize tensor
values, or claim native performance parity.

## Motivation

Runtime Backend Equivalence already has individual reports and a portfolio.
Those reports are complete but not ideal as the first proof a reviewer should
read. The Universal Compute claim needs one visible proof entrypoint for:

- same compute intent;
- neutral `reference-cpu` baseline;
- mixed `systolic-sim + vector-sim` candidate placement;
- matched terminal output semantics;
- metadata-only evidence.

## Decision

Add:

- `examples/proof_of_backend_equivalence.py`
- `schemas/proof_of_backend_equivalence_report.v0.schema.json`
- `tests/golden/proofs/proof_of_backend_equivalence.json`
- `tests/test_proof_of_backend_equivalence.py`

The proof wraps the existing mixed Runtime Backend Equivalence report. It binds
to that report by SHA-256 digest and emits only the proof facts needed for a
first read:

- graph name;
- baseline and candidate run IDs;
- baseline and candidate backend sequences;
- terminal output comparison status;
- runtime equivalence report digest;
- raw-value omission policy;
- blocked execution surfaces;
- explicit non-claims.

## Security Boundary

The proof report is metadata-only. It must not contain raw tensor values,
tensor-value digests, runtime handles, allocation handles, device identifiers,
host paths, command lines, environment variables, generated code, backend
artifacts, plugin entrypoints, dynamic-library paths, raw benchmark samples, or
native execution claims.

The schema is fail-closed with `additionalProperties: false` for every object.

## Consequences

- Backend Equivalence becomes easier to discover as a first-class TUC proof.
- The runtime proof remains grounded in the existing mixed backend equivalence
  report instead of duplicating executor behavior.
- Native execution, performance parity, plugin safety, and broad source-parser
  correctness remain blocked.
