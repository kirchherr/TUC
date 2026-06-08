# Proof Of Abstraction

The proof-of-abstraction example is TUC's first Objective Alpha artifact from
the master plan.

It demonstrates:

```text
Graph
    ->
HAC-IR
    ->
Runtime Planning
    ->
Backend A
    ->
Backend B
    ->
Correct Result
```

The proof is intentionally about mathematical correctness and inspectability,
not performance.

## Run It

```bash
python examples/proof_of_abstraction.py
```

Expected final line:

```text
PASS
```

## What It Shows

The example builds a two-operation graph:

- `linear_projection`: a matmul assigned to the `linear-sim` backend.
- `digital_activation`: a ReLU elementwise operation assigned to the `gpu`
  fallback backend.

It prints:

- input graph
- HAC-IR
- backend assignments
- transfer plan
- result
- independent reference result
- PASS/FAIL

## Reproducibility Contract

The complete output is stored as a golden artifact:

```text
tests/golden/proofs/proof_of_abstraction.txt
```

`tests/test_proof_of_abstraction.py` runs the example and compares its full
stdout to that golden file.

The runtime plan inside the proof also has its own narrower golden contract:

```text
tests/golden/runtime_plans/proof_of_abstraction.txt
```

`tests/test_runtime_plan_golden.py` compares the proof's runtime plan dump to
that artifact. This makes placement and transfer reasoning reviewable without
requiring maintainers to diff the full proof report.

This keeps the proof aligned with the master plan's Level 3 validation target:
another person can reproduce the same proof and see the same report.

## Security Notes

The proof uses only:

- bounded in-repository graph definitions
- validated HAC-IR lowering
- pure backend capability data
- deterministic reference kernels
- runtime planning dumps

It does not import external backend code, discover plugins, access devices,
execute generated artifacts, or depend on vendor hardware.
