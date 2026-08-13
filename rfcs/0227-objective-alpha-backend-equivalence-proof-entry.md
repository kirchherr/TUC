# RFC 0227: Objective Alpha Backend Equivalence Proof Entry

- Status: accepted-for-prototype
- Created: 2026-06-26
- Phase: Alpha / Delta

## Summary

Expose Proof Of Backend Equivalence as a fixed digest-only entry in the
Objective Alpha Public Proof Bundle.

This RFC does not add a new runtime executor, parse source code, execute backend
plugins, access devices, load dynamic libraries, serialize tensor values, or
claim native performance parity.

## Motivation

The Universal Compute research claim is clearest when the first public bundle
shows not only that TUC can execute a controlled proof path, but also that the
same neutral compute intent preserves terminal semantics across a mixed trusted
backend placement.

`examples/proof_of_backend_equivalence.py` already provides the canonical
metadata-only proof for `reference-cpu` versus `systolic-sim + vector-sim`. The
Objective Alpha bundle should bind that proof directly so reviewers can find it
without unpacking Runtime Evidence Gate internals.

## Decision

Add one fixed bundle entry:

- Evidence ID: `proof_of_backend_equivalence`
- Entry point: `python examples/proof_of_backend_equivalence.py`
- Artifact kind: `schema_versioned_backend_equivalence_proof_report`
- Raw output policy: `digest_only`

The bundle records only a SHA-256 digest of the proof output plus fixed entry
metadata. The proof output itself remains governed by
`schemas/proof_of_backend_equivalence_report.v0.schema.json`.

## Security Boundary

The bundle remains metadata-only. It must not contain raw tensor values,
tensor-value digests, runtime handles, allocation handles, device identifiers,
host paths, command lines, environment variables, generated code, backend
artifacts, plugin entrypoints, dynamic-library paths, raw benchmark samples, or
native execution claims.

The schema keeps fixed entry IDs, fixed entry points, fixed artifact kinds,
`additionalProperties: false`, and exact entry count checks.

## Consequences

- Backend Equivalence becomes visible in the top-level Objective Alpha review
  artifact.
- The public proof path now binds execution, evidence gates, backend-equivalence
  semantics, output closure, transfer-boundary replay, memory planning, and
  onboarding in one digest-only bundle.
- Native performance, physical device residency, broad source parsing, and
  vendor compiler replacement remain blocked claims.