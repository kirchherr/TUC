# Objective Alpha Evidence Extension Policy

Objective Alpha's public proof bundle is intentionally fixed at sixteen
digest-only entries. This policy defines how future evidence may grow without
changing that stable reviewer entrypoint by accident.

Run it with:

```bash
python examples/objective_alpha_evidence_extension_policy.py
```

The report is schema-versioned at:

```text
schemas/objective_alpha_evidence_extension_policy_report.v0.schema.json
```

Golden evidence lives at:

```text
tests/golden/proofs/objective_alpha_evidence_extension_policy.json
```

## What It Proves

The policy proves that the current Objective Alpha public proof bundle is a
stable entrypoint with `entry_capacity: 16` and `entry_count: 16`, and that new
public evidence must not be appended to that bundle without a deliberate RFC or
a separate public evidence catalog/successor objective.

That separate catalog now exists as
[Objective Alpha Public Evidence Catalog](OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md),
with example `examples/objective_alpha_public_evidence_catalog.py`, schema
`schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json`, and
golden `tests/golden/proofs/objective_alpha_public_evidence_catalog.json`.
Canonical doc path: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md`.

This keeps the first reviewer path small while allowing TUC to continue adding
research evidence behind a controlled extension surface.

## Required Controls

Future public evidence extensions must stay:

- schema-versioned;
- digest-only;
- source-free in public reports;
- free of execution handles;
- free of device access;
- free of generated-artifact execution;
- free of native performance claims.

## Blocked Changes

The policy blocks these changes unless a new RFC deliberately changes the
boundary:

- increasing Objective Alpha public bundle capacity;
- replacing public bundle entries;
- adding source buffers to public artifacts;
- adding tensor values to public artifacts;
- authorizing execution handles;
- authorizing device access;
- authorizing generated-artifact execution;
- claiming native performance.

## Non-Claims

This policy does not prove native performance, broad source parsing, vendor
compiler replacement, third-party backend execution, or hardware residency. It
only protects the public evidence growth path after the first Objective Alpha
bundle reached its fixed capacity.
