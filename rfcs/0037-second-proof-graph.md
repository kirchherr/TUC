# RFC 0037: Second Proof Graph

- Status: accepted-for-prototype
- Created: 2026-06-08
- Phase: Alpha

## Summary

TUC adds a second Objective Alpha proof graph that includes a sum reduction.

The new example is `examples/proof_of_reduction.py`. It follows the same proof
shape as the original abstraction proof while expanding the covered MVP
operation families.

## Motivation

The first proof shows that matmul and elementwise intent can flow through
HAC-IR, runtime planning, backend assignment, and deterministic reference
validation. The roadmap calls for a second proof using reduction or softmax so
the public proof does not look like a single tailored graph.

Reduction is the smallest next operation family because it is already part of
the HAC-IR and HS-IR v0 contracts, has deterministic reference semantics, and
is supported by the linear simulator capability model.

## Decision

Add a proof graph with this shape:

```text
matmul
    ->
reduction
    ->
elementwise
```

Runtime planning assigns:

- matmul to `linear-sim`
- reduction to `linear-sim`
- elementwise activation to the `gpu` fallback

Add golden artifacts for:

- full proof stdout
- HAC-IR dump
- runtime-plan dump

Add `docs/PROOF_OF_REDUCTION.md` so reviewers can understand how to run and
interpret the proof.

## Security Model

The proof introduces no new parser, plugin, native-code, device, or artifact
execution surface.

The example uses fixed in-repository graph construction, bounded tensor shapes,
validated compiler lowering, trusted in-memory backend capability data, and
deterministic NumPy reference kernels. Tests compare repository-owned text
fixtures rather than executing generated code.

## Consequences

- Objective Alpha now has more than one proof graph.
- HAC-IR coverage includes a reduction operation in a full proof path.
- Runtime-plan golden fixtures now cover a linear simulator reduction followed
  by a fallback transfer.
- Reviewers can distinguish intentional proof-contract changes from accidental
  dump drift.

## Alternatives Considered

1. Add softmax first.

   Deferred because softmax is nonlinear and currently handled by reference
   fixtures rather than the linear simulator backend. It remains valuable, but
   reduction gives the smallest additional proof without changing backend
   capability boundaries.

2. Add a much larger model-like graph.

   Rejected for Objective Alpha because the master plan values the smallest
   unarguable proof over architecture inflation.

3. Add runtime scoring before the second proof.

   Rejected because the current rule-based planner is intentionally easier to
   inspect. Candidate scoring belongs after the proof artifacts remain stable.

## Follow-Up

1. Add proof report metadata for proof version, graph family, and backend set.
2. Add a reviewer-facing checklist for changing proof artifacts.
3. Add a future softmax proof after nonlinear operation-family planning is
   documented.
