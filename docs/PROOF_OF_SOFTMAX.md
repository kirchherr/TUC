# Proof Of Softmax

The softmax proof is TUC's third Objective Alpha proof artifact.

It extends the proof ladder with the `softmax` MVP operation family while
preserving the same central claim:

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

The proof is intentionally small. It demonstrates stable nonlinear reference
semantics, explicit axis validation, hardware-independent HAC-IR intent,
explainable runtime fallback, and reproducible golden artifacts.

## Run It

```bash
python examples/proof_of_softmax.py
```

Expected final line:

```text
PASS
```

## What It Shows

The example builds a two-operation graph:

- `linear_projection`: a matmul assigned to the `linear-sim` backend.
- `row_softmax`: a row-wise softmax assigned to the `gpu` fallback backend.

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
tests/golden/proofs/proof_of_softmax.txt
```

`tests/test_proof_of_softmax.py` runs the example and compares its full stdout
to that golden file.

The report starts with metadata:

```text
report_schema: proof-report.v0
proof_id: proof_of_softmax
proof_version: alpha.v1
graph_family: softmax
backend_set: gpu, linear-sim
```

This makes proof version, graph family, and backend set visible before HAC-IR,
runtime planning, or numerical output.

The HAC-IR dump also has its own narrower golden contract:

```text
tests/golden/hac_ir/proof_of_softmax.txt
```

The runtime plan has its own golden contract:

```text
tests/golden/runtime_plans/proof_of_softmax.txt
```

The compiler decision report has its own golden contract:

```text
tests/golden/compiler_decisions/proof_of_softmax.txt
```

Together these artifacts let reviewers inspect compute intent, movement facts,
backend support diagnostics, fallback assignment, transfer bytes, and numerical
correctness independently.

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
