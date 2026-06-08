# Proof Of Reduction

The reduction proof is TUC's second Objective Alpha proof artifact.

It extends the first proof-of-abstraction graph with the `reduction` MVP
operation family while preserving the same central claim:

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

The proof remains intentionally small. It demonstrates mathematical
correctness, hardware-independent HAC-IR intent, explainable runtime planning,
and reproducible golden artifacts.

## Run It

```bash
python examples/proof_of_reduction.py
```

Expected final line:

```text
PASS
```

## What It Shows

The example builds a three-operation graph:

- `linear_projection`: a matmul assigned to the `linear-sim` backend.
- `row_reduction`: a sum reduction assigned to the `linear-sim` backend.
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
tests/golden/proofs/proof_of_reduction.txt
```

`tests/test_proof_of_reduction.py` runs the example and compares its full
stdout to that golden file.

The report starts with metadata:

```text
report_schema: proof-report.v0
proof_id: proof_of_reduction
proof_version: alpha.v1
graph_family: reduction
backend_set: gpu, linear-sim
```

This makes proof version, graph family, and backend set visible before HAC-IR,
runtime planning, or numerical output.

The HAC-IR dump also has its own narrower golden contract:

```text
tests/golden/hac_ir/proof_of_reduction.txt
```

The runtime plan has its own golden contract:

```text
tests/golden/runtime_plans/proof_of_reduction.txt
```

Together these artifacts let reviewers inspect compute intent, movement facts,
backend assignments, transfer bytes, and correctness independently.

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
