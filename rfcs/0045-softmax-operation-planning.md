# RFC 0045: Softmax Operation-Family Planning

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Beta/Gamma/Delta

## Summary

TUC defines the softmax operation-family planning contract before adding
softmax proof graphs or softmax-specific HAC-IR, runtime-plan, and compiler
decision-report goldens.

The contract lives in `docs/SOFTMAX_OPERATION_PLANNING.md`.

## Motivation

Softmax is nonlinear and numerically sensitive. It combines max-reduction,
exponentiation, sum-reduction, and normalization. Treating it as ordinary
elementwise work would hide the exact boundary TUC needs to prove:

```text
HAC-IR preserves hardware-independent softmax intent.
Runtime planning explains placement or decomposition.
Backends cannot redefine softmax semantics.
```

## Decision

Softmax remains a first-class MVP operation family in HAC-IR.

Future softmax proof graphs must:

- use stable reference semantics based on max-shifted softmax
- validate axis, rank, input shape, output shape, dtype, and finite inputs
- keep softmax linearity as `nonlinear`
- keep decomposition out of HAC-IR semantics
- expose placement, fallback, transfer, layout, override, and candidate-score
  evidence through runtime plans and compiler decision reports
- fail closed when decomposition, approximation, or backend support would
  change semantics without an explicit proof contract

## Security Model

Softmax planning is declarative documentation and review policy.

It does not:

- execute backend code
- discover plugins
- import modules
- spawn subprocesses
- load dynamic libraries
- access devices
- execute generated artifacts
- touch the network
- read host paths
- read environment variables
- add a parser surface
- add a backend artifact path

Future softmax implementation PRs must preserve these boundaries and add
negative tests for malformed axes, shape mismatches, unsupported decomposition
claims, and misleading backend capability claims.

## Consequences

- HAC-IR softmax semantics are separated from runtime decomposition choices.
- Future softmax goldens have a required review checklist.
- Backend authors cannot claim softmax support by exposing only hidden
  backend-specific decomposition details.
- Runtime candidate diagnostics have a clear future home for softmax-specific
  score components.

## Follow-Up

1. Add a softmax HAC-IR golden once the proof graph is introduced.
2. Add runtime-plan and compiler decision-report goldens for the same graph.
3. Add a proof report that validates against `reference_softmax(...)` and ends
   in `PASS`.
4. Add decomposition-specific negative tests before any runtime decomposition
   path is implemented.

