# RFC 0144: Runtime Evidence Matrix Portfolio Inventory

## Status

Accepted.

## Context

Runtime Backend Equivalence Portfolio v0 aggregates the systolic, vector, and
mixed accelerator equivalence reports into one backend-diversity artifact. The
Runtime Evidence Gate already binds that portfolio back to the exact reports it
checks.

However, if the portfolio only exists inside gate-local logic, the Runtime
Evidence Matrix does not visibly inventory backend-diversity evidence. That
weakens reviewability because the proof inventory and the gate can drift in
meaning.

## Decision

Runtime Evidence Matrix now includes a dedicated graph:

```text
runtime_backend_equivalence_portfolio
```

The graph uses:

- graph family: `backend_equivalence_portfolio`
- source boundary: `runtime_backend_equivalence`
- required artifact kinds: `backend_equivalence_portfolio` and
  `backend_equivalence_portfolio_policy`
- artifact ID: `runtime_backend_equivalence_portfolio`
- policy artifact ID: `runtime_backend_equivalence_portfolio_policy`

Runtime Evidence Gate now verifies this Matrix coverage before portfolio
evidence can count as passing merge evidence.

## Security Boundary

This remains metadata-only. The Matrix does not resolve artifact IDs to paths,
scan files, discover backends, import plugins, access devices, spawn
subprocesses, touch the network, run JIT code, load dynamic libraries, execute
generated artifacts, or authorize native execution.

The new artifact kind is a bounded identifier. It does not introduce serialized
tensor values, runtime handles, host paths, device identifiers, generated code,
commands, plugin entrypoints, benchmark output, or backend artifacts.

## Consequences

Backend-diversity evidence is now visible in both places:

- Runtime Evidence Matrix as scoped proof-inventory coverage
- Runtime Evidence Gate as a bound, checked aggregate over the exact
  equivalence reports evaluated by the gate

Future backend families should add their individual equivalence slice and then
extend both the portfolio and Matrix inventory before stronger portability
claims are accepted.
