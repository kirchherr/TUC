# Reproducing Objective Beta

This is the shortest independent review path for the current TUC research
claim. It uses the project container and versioned evidence only.

## One-Minute Replay

From the repository root:

```bash
docker compose build dev
docker compose run --rm -T dev python examples/objective_beta_reproducibility_capsule.py
docker compose run --rm -T dev python examples/objective_beta_reproducibility_gate.py
```

The final command must report `gate_status: PASS`, nine verified artifacts, a
verified claim link, verified evidence links, and
`source_ingestion_admitted: false`.

## Focused Validation

```bash
docker compose run --rm -T dev pytest -q \
  tests/test_objective_beta_reproducibility_capsule.py \
  tests/test_objective_beta_reproducibility_gate.py
```

The negative tests deliberately modify artifact bytes, extend the allowlist,
attempt source-field leakage, reorder evidence, and open blocked claim flags.
Every case must fail closed.

## What Was Reproduced

The replay verifies the integrity closure:

```text
Objective Alpha gate
        +
Kernel-ingress and first-slice evidence
        +
Research-scope boundary
        ->
Objective Beta claim
        ->
Objective Beta claim gate
        ->
Offline reproducibility PASS
```

It does not rerun numerical execution. Numerical, backend-equivalence, runtime,
layout-conversion, and Source-to-Intent results are already committed as the
versioned evidence bound through the claim chain. Reviewers who want to rerun
those individual proofs can follow [Minimal TUC Walkthrough](MINIMAL_TUC_WALKTHROUGH.md)
and [Proof Of Backend Equivalence](PROOF_OF_BACKEND_EQUIVALENCE.md).

## Interpretation

A PASS means the current bounded Objective Beta research claim is reproducible
from the checked-out repository state and has not drifted from its declared
evidence. It does not mean source ingestion is approved, hardware was accessed,
or native performance was measured.
