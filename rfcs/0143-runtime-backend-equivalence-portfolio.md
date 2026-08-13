# RFC 0143: Runtime Backend Equivalence Portfolio

## Status

Accepted.

## Context

TUC now has three Backend Equivalence proof slices:

- `reference-cpu` versus `systolic-sim`
- `reference-cpu` versus `vector-sim`
- `reference-cpu` versus mixed `systolic-sim` and `vector-sim`

Each slice is useful on its own, but The Universal Compute claim needs a
review surface that shows backend diversity as an explicit aggregate. Without
that surface, the Runtime Evidence Gate risks becoming a list of independent
checks without a named portfolio contract.

## Decision

Introduce Runtime Backend Equivalence Portfolio v0.

The portfolio is a schema-versioned, data-only artifact with schema:

```text
schemas/runtime_backend_equivalence_portfolio_report.v0.schema.json
```

It aggregates Backend Equivalence reports by recording:

- slice ID and graph name
- baseline and candidate run IDs
- baseline and candidate backend sequences
- comparison count
- comparison metadata digest
- pass status
- raw-value policy

The current deterministic example is:

```text
examples/runtime_backend_equivalence_portfolio.py
```

The current golden artifact is:

```text
tests/golden/runtime_backend_equivalence/portfolio_report.json
```

Runtime Evidence Gate builds the portfolio from the exact Backend Equivalence
reports it already checked and then verifies the portfolio binding before the
gate can pass.

## Security Boundary

This portfolio is metadata-only. It does not execute reports, resolve artifact
IDs, discover backends, load plugins, access devices, spawn subprocesses, touch
the network, run JIT code, load dynamic libraries, execute generated artifacts,
or authorize native execution.

It does not serialize tensor values, tensor-value digests, runtime handles,
host paths, device identifiers, generated code, plugin entrypoints, commands,
environment variables, raw benchmark output, backend artifacts, or raw
execution output.

## Consequences

Backend Equivalence evidence now has two layers:

- individual report evidence for each trusted backend placement comparison
- portfolio evidence proving the accepted backend-diversity set is coherent

New backend families should add an individual equivalence slice first, then be
added to the portfolio and Runtime Evidence Gate binding before they support
stronger Universal Compute portability claims.
