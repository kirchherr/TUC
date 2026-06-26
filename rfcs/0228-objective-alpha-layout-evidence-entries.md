# RFC 0228: Objective Alpha Layout Evidence Entries

- Status: accepted-for-prototype
- Created: 2026-06-26
- Phase: Alpha / Delta

## Summary

Expose layout-transition replay and backend-equivalence layout binding as fixed
digest-only entries in the Objective Alpha Public Proof Bundle.

This RFC does not add runtime layout converters, execute backend plugins, access
devices, materialize transfer or layout-conversion steps, serialize tensor
values, or claim physical device residency or native performance parity.

## Motivation

The Universal Compute proof needs layout transitions to remain explicit instead
of becoming hidden backend-local behavior. Runtime Evidence Gate already requires
layout-conversion evidence for the mixed backend-equivalence graph. The public
bundle should expose the same proof chain so reviewers can see that mixed backend
terminal semantics and layout-transition replay evidence are bound together.

## Decision

Add two fixed bundle entries:

- Evidence ID: `runtime_layout_conversion_trace_replay_verifier`
- Entry point: `python examples/runtime_layout_conversion_trace_replay_verifier.py`
- Artifact kind: `schema_versioned_layout_conversion_trace_replay_verifier_report`
- Raw output policy: `digest_only`

and:

- Evidence ID: `runtime_backend_equivalence_layout_binding`
- Entry point: `python examples/runtime_backend_equivalence_layout_binding.py`
- Artifact kind: `schema_versioned_backend_equivalence_layout_binding_report`
- Raw output policy: `digest_only`

The bundle records only SHA-256 digests of those reports plus fixed entry
metadata. The underlying reports remain governed by their schema-versioned
contracts.

## Security Boundary

The bundle remains metadata-only. It must not contain raw tensor values,
tensor-value digests, runtime handles, allocation handles, device identifiers,
host paths, command lines, environment variables, generated code, backend
artifacts, plugin entrypoints, dynamic-library paths, raw benchmark samples,
layout-converter artifacts, or native execution claims.

The schema keeps fixed entry IDs, fixed entry points, fixed artifact kinds,
`additionalProperties: false`, and exact entry count checks.

## Consequences

- Layout transitions become visible in the top-level Objective Alpha review
  artifact without opening a native converter surface.
- The public proof path now binds backend-equivalence semantics to both transfer
  and layout replay evidence by digest.
- Physical device residency, native layout conversion, broad source parsing, and
  native performance remain blocked claims.