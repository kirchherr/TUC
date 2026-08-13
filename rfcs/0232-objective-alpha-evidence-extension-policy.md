# RFC 0232: Objective Alpha Evidence Extension Policy

## Status

Accepted.

## Context

Objective Alpha Public Proof Bundle v0 now exposes sixteen fixed digest-only
entries and reports both `entry_count: 16` and `entry_capacity: 16`. That is a
useful reviewer boundary: it keeps the first public proof path stable and
small enough to audit.

The next risk is evidence growth by accretion. If every new proof becomes one
more public bundle entry, the stable entrypoint becomes difficult to review and
TUC loses the clarity gained by the README and bundle cleanup.

## Decision

Add Objective Alpha Evidence Extension Policy v0 as a data-only report:

- example: `examples/objective_alpha_evidence_extension_policy.py`
- schema: `schemas/objective_alpha_evidence_extension_policy_report.v0.schema.json`
- golden: `tests/golden/proofs/objective_alpha_evidence_extension_policy.json`
- docs: `docs/OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY.md`

The policy binds to the passing Objective Alpha Public Proof Bundle Gate and
requires the current public bundle to remain full and fixed before it can pass.
It does not add entries to the public bundle.

## Required Controls

Future public evidence extensions must be schema-versioned, digest-only,
source-free in public reports, and free of execution handles, device access,
generated-artifact execution, and native performance claims.

## Blocked Changes

Without a deliberate RFC, TUC must not:

- increase Objective Alpha Public Proof Bundle capacity;
- replace fixed public bundle entries;
- add source buffers or tensor values to public artifacts;
- authorize execution handles or device access;
- authorize generated-artifact execution;
- claim native performance.

## Consequences

Objective Alpha stays a stable first public proof entrypoint. Future evidence
can still grow, but it must either use a separate public evidence catalog or a
successor objective with its own schema and review policy.

This keeps the research path expandable without diluting the core claim.
