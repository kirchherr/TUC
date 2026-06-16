# Source-To-Intent Research Kernel Ingress

Source-To-Intent Research Kernel Ingress v0 is the first realistic
Triton-module-shaped source path for the current research parser.

It accepts a caller-provided module source buffer shaped like:

```text
allowed Triton import prelude
    ->
one @triton.jit kernel function
```

The module is parsed as bounded AST data only. TUC does not import the module,
evaluate decorators, inspect live Python functions, execute JIT code, read
files, access devices, or discover plugins.

## Contract

- Frontend ingress contract:
  `source_to_intent_research_kernel_ingress.execution_free.v0`
- End-to-end proof contract:
  `source_to_intent_research_kernel_ingress.e2e.v0`
- End-to-end report schema:
  `schemas/source_to_intent_research_kernel_ingress_e2e_report.v0.schema.json`
- Frontend API:
  `src/tuc/frontend/source_to_intent_research_kernel_ingress.py`
- Example: `examples/source_to_intent_research_kernel_ingress.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress.json`
- Tests: `tests/test_source_to_intent_research_kernel_ingress.py`
- Digest binding: `examples/source_to_intent_research_evidence_gate.py`
- Proof bundle binding: `examples/source_to_intent_research_proof_bundle.py`
- Boundary budget companion:
  `examples/source_to_intent_research_kernel_ingress_boundary_budget.py`
- Boundary budget docs:
  [Source-To-Intent Research Kernel Ingress Boundary Budget](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET.md)
- Conformance gate companion:
  `examples/source_to_intent_research_kernel_ingress_conformance_gate.py`
- Conformance gate docs:
  [Source-To-Intent Research Kernel Ingress Conformance Gate](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE.md)
- Diagnostics companion:
  `examples/source_to_intent_research_kernel_ingress_diagnostics.py`
- Diagnostics docs:
  [Source-To-Intent Research Kernel Ingress Diagnostics](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS.md)
- Idiom alignment companion:
  `examples/source_to_intent_research_kernel_ingress_idiom_alignment.py`
- Idiom alignment docs:
  [Source-To-Intent Research Kernel Ingress Idiom Alignment](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT.md)
- Proof bundle companion:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- Proof bundle docs:
  [Source-To-Intent Research Kernel Ingress Proof Bundle](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md)
- CI entry: `.github/workflows/ci.yml`

## Accepted Module Shape

The v0 ingress accepts exactly:

- `import triton`
- `import triton.language as tl`
- one top-level kernel function selected by explicit `kernel_name`

The extracted function source then re-enters the existing execution-free
Triton Source Preflight and explicit Source-To-Intent Research Parser path.

## Proof Path

The example proves both accepted module-source fixtures through:

```text
Triton module source buffer
    ->
Kernel Ingress validation and extraction
    ->
Triton Source Preflight
    ->
Explicit Research Parser
    ->
source_intent.v0 plain data
    ->
Source Intent Intake
    ->
Metadata Conversion
    ->
HAC-IR and Runtime Plan
    ->
Runtime Executor
    ->
Runtime Reference Correctness
```

## Security Boundary

The report is metadata-only. It records digests, statuses, operation families,
backend sequences, and runtime evidence digests, but omits raw module source,
raw extracted kernel source, raw Source Intent payloads, tensor values, compiler
artifacts, backend binaries, command lines, host paths, environment variables,
device identifiers, generated code, and benchmark output.

The ingress keeps these claims blocked:

- `general_triton_source_ingestion`
- `native_performance_claim`
- `production_parser`

The companion Kernel Ingress Idiom Alignment report proves that accepted
module-shaped outputs still map only to the covered Triton MVP idioms:
matmul, elementwise, reduction, and softmax.

The companion Kernel Ingress Boundary Budget report proves accepted
module-shaped inputs stay within byte, line, AST-node, and AST-depth budgets,
and that byte/line budget overflows reject before extraction or lowering.

The companion Kernel Ingress Proof Bundle gives reviewers a digest-only index
for the Kernel Ingress E2E, boundary-budget, diagnostics, conformance, and
idiom-alignment artifacts.

## Review Meaning

This is a credible research step toward the roadmap's first real Triton kernel
ingestion path. It proves that a realistic module-shaped source buffer can feed
the existing safe source-to-runtime slice, while default source parser intake
remains blocked.
