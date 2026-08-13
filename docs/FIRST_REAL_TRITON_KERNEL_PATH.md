# First Real Triton Kernel Path

First Real Triton Kernel Path v0 is the short, reviewer-facing proof that the
current TUC research stack can carry one realistic Triton-module-shaped MVP
kernel through controlled Kernel Ingress, Source Intent re-intake, capability
planning, trusted prototype runtime execution, backend-equivalence evidence,
and fail-closed source-ingestion admission boundaries.

It is intentionally narrower than the Kernel Ingress Proof Bundle. The proof
focuses on the single accepted `mvp_pipeline` case:

```text
module-shaped source buffer
  -> controlled kernel extraction
  -> Source Intent plain data
  -> ComputeGraph compile
  -> trusted prototype runtime execution
  -> backend-equivalence metadata check
  -> source-ingestion admission remains closed
```

## Contract

- Proof contract:
  `first_real_triton_kernel_path.digest_bound.v0`
- Report schema:
  `schemas/first_real_triton_kernel_path_report.v0.schema.json`
- Example:
  `examples/first_real_triton_kernel_path.py`
- Golden:
  `tests/golden/frontend/first_real_triton_kernel_path.json`
- Tests:
  `tests/test_first_real_triton_kernel_path.py`
- RFC:
  `rfcs/0272-first-real-triton-kernel-path.md`
- CI entry: `.github/workflows/ci.yml`

## Current Proof

The current case is `research_module_mvp_pipeline` / `mvp_pipeline`.

It binds these expected public semantics:

- operation families: `elementwise`, `matmul`, `reduction`, `softmax`
- backend sequence: `linear-sim`, `vector-sim`, `vector-sim`, `vector-sim`
- terminal output: `stable`
- runtime trace steps: `4`

## Bound Evidence

The report records SHA-256 digests for:

- `examples/source_to_intent_research_kernel_ingress.py`
- `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
- `examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py`
- `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- `examples/source_ingestion_preclaim_acyclicity_gate.py`
- `examples/source_ingestion_admission_gate.py`

This makes the proof easy to read while keeping the stronger underlying
evidence reusable.

## Blocked Claims

The proof explicitly does not claim:

- arbitrary Triton source ingestion
- a production parser
- native backend execution
- native performance parity
- CUDA replacement
- runtime-handle residency

## Security Boundary

The report is digest-only and source-free. It does not serialize module source,
extracted kernel source, Source Intent payloads, tensor values, generated code,
backend artifacts, command lines, host paths, device identifiers, runtime
handles, or native benchmark output.

It does not import Triton, evaluate decorators, run `@triton.jit`, touch real
devices, load plugins, execute generated artifacts, or admit direct source
ingestion. The source-ingestion admission gate remains blocked until external
maintainer security review approval exists.

## Why This Exists

The broad roadmap can look larger than the core claim. This proof gives a
compact answer to the practical research question:

```text
Can one realistic Triton-shaped kernel path traverse TUC's neutral interface
and produce reviewable runtime and equivalence evidence without opening unsafe
execution surfaces?
```

Current answer: `PASS` for the bounded `mvp_pipeline` research case.
## Portfolio Binding

The broader first-slice milestone is
[Real Triton First Slice Evidence Portfolio](REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO.md).
It binds this proof together with the first-slice plan, maintainer review,
missing approval artifact, fail-closed admission gate, pre-claim acyclicity,
and Research Scope Claim Gate.

Canonical portfolio doc path: `docs/REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO.md`

Portfolio example: `examples/real_triton_first_slice_evidence_portfolio.py`

Portfolio schema:
`schemas/real_triton_first_slice_evidence_portfolio_report.v0.schema.json`

Portfolio golden:
`tests/golden/frontend/real_triton_first_slice_evidence_portfolio_report.json`

Portfolio RFC: `rfcs/0274-real-triton-first-slice-evidence-portfolio.md`
