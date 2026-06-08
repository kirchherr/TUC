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

- proof metadata
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

The report starts with metadata:

```text
report_schema: proof-report.v0
proof_id: proof_of_abstraction
proof_version: alpha.v1
graph_family: abstraction
backend_set: gpu, linear-sim
```

This makes proof version, graph family, and backend set visible before HAC-IR,
runtime planning, or numerical output.

The runtime plan inside the proof also has its own narrower golden contract:

```text
tests/golden/runtime_plans/proof_of_abstraction.txt
```

`tests/test_runtime_plan_golden.py` compares the proof's runtime plan dump to
that artifact. This makes placement and transfer reasoning reviewable without
requiring maintainers to diff the full proof report.

The HAC-IR dump has a separate golden contract:

```text
tests/golden/hac_ir/proof_of_abstraction.txt
```

`tests/test_hac_ir_golden_dumps.py` compares the proof graph's HAC-IR dump to
that artifact. This keeps hardware-independent compute intent reviewable on its
own, before runtime planning and backend assignment enter the report.

This keeps the proof aligned with the master plan's Level 3 validation target:
another person can reproduce the same proof and see the same report.

The second Objective Alpha proof is documented in
[`PROOF_OF_REDUCTION.md`](PROOF_OF_REDUCTION.md). The third Objective Alpha
proof is documented in [`PROOF_OF_SOFTMAX.md`](PROOF_OF_SOFTMAX.md).

Changes to proof artifacts must follow the
[`PROOF_ARTIFACT_REVIEW.md`](PROOF_ARTIFACT_REVIEW.md) checklist.

## Security Notes

The proof uses only:

- bounded in-repository graph definitions
- validated HAC-IR lowering
- pure backend capability data
- deterministic reference kernels
- runtime planning dumps

It does not import external backend code, discover plugins, access devices,
execute generated artifacts, or depend on vendor hardware.
