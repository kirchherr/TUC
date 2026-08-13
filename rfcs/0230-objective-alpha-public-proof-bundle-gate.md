# RFC 0230: Objective Alpha Public Proof Bundle Gate

- Status: accepted-for-prototype
- Created: 2026-06-26
- Phase: Alpha / Delta

## Summary

Add a data-only gate report for the Objective Alpha Public Proof Bundle.

This RFC does not add new runtime execution, execute bundle entry point strings,
resolve filesystem paths, run subprocesses, access devices, discover plugins,
load dynamic libraries, parse source code, or claim native performance parity.

## Motivation

The public Objective Alpha bundle is now the main reviewer entrypoint for TUC's
current proof path. As the bundle grows to expose backend-equivalence, transfer,
layout, memory-planning, and onboarding evidence, reviewers need a small stable
gate that proves the bundle itself has not drifted beyond its accepted contract.

## Decision

Add:

- `examples/objective_alpha_public_proof_bundle_gate.py`
- `schemas/objective_alpha_public_proof_bundle_gate_report.v0.schema.json`
- `docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md`
- `tests/golden/proofs/objective_alpha_public_proof_bundle_gate_report.json`
- `tests/test_objective_alpha_public_proof_bundle_gate.py`

The gate emits only bounded metadata:

- bundle ID and contract;
- bundle metadata digest;
- fixed evidence IDs;
- fixed entry points;
- fixed artifact kinds;
- entry and digest counts;
- digest policy;
- direct transfer-trace-index and layout-conversion-trace-index public-entry
  invariants;
- blocked claims and execution surfaces;
- non-claim booleans;
- derived pass/fail status.

The gate is intentionally not inserted into the bundle it validates.

## Security Boundary

The gate validates the trusted in-memory bundle model. It must not execute entry
point strings, run shell commands, resolve artifact paths, import backend
plugins, access devices, run JIT code, touch the network, serialize raw tensor
values, expose runtime handles, expose host paths, or include generated code.

The schema is fail-closed with `additionalProperties: false` for every object.

## Consequences

- The public proof bundle gains a direct CI/review guardrail.
- Transfer and layout trace indexes stay reviewable as explicit public entries,
  not just as indirect prerequisites of replay or binding reports.
- Future bundle changes must update the gate schema, golden, docs, and tests.
- Native execution, broad source parsing, vendor replacement, device access, and
generated-artifact execution remain blocked claims.
