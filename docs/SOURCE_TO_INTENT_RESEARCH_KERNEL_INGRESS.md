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
- Runtime matrix companion:
  `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
- Runtime matrix docs:
  [Source-To-Intent Research Kernel Ingress Runtime Matrix](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX.md)
- Runtime step trace companion:
  `examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py`
- Runtime step trace docs:
  [Source-To-Intent Research Kernel Ingress Runtime Step Trace](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE.md)
- Runtime evidence bundle index companion:
  `examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`
- Runtime evidence bundle index docs:
  [Source-To-Intent Research Kernel Ingress Runtime Evidence Bundle Index](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX.md)
- Runtime output closure index companion:
  `examples/source_to_intent_research_kernel_ingress_runtime_output_closure_index.py`
- Runtime output closure index docs:
  [Source-To-Intent Research Kernel Ingress Runtime Output Closure Index](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_OUTPUT_CLOSURE_INDEX.md)
- Runtime coverage policy companion:
  `examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`
- Runtime coverage policy docs:
  [Source-To-Intent Research Kernel Ingress Runtime Coverage Policy](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY.md)
- Runtime backend alignment companion:
  `examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`
- Runtime backend alignment docs:
  [Source-To-Intent Research Kernel Ingress Runtime Backend Alignment](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT.md)
- Boundary budget companion:
  `examples/source_to_intent_research_kernel_ingress_boundary_budget.py`
- Boundary budget docs:
  [Source-To-Intent Research Kernel Ingress Boundary Budget](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET.md)
- Rejection coverage companion:
  `examples/source_to_intent_research_kernel_ingress_rejection_coverage.py`
- Rejection coverage docs:
  [Source-To-Intent Research Kernel Ingress Rejection Coverage](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE.md)
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
- Evidence gate companion:
  `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- Evidence gate docs:
  [Source-To-Intent Research Kernel Ingress Evidence Gate](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md)
- Capability claim consumer:
  `examples/source_to_intent_research_capability_claim.py`
- CI entry: `.github/workflows/ci.yml`
- Fixture expansion RFC:
  `rfcs/0176-source-to-intent-research-kernel-ingress-fixture-expansion.md`
- Combined MVP pipeline RFC:
  `rfcs/0177-source-to-intent-research-kernel-ingress-combined-mvp-pipeline.md`
- Backend equivalence companion:
  [Source-To-Intent Research Kernel Ingress Backend Equivalence](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE.md)
- Backend equivalence example:
  `examples/source_to_intent_research_kernel_ingress_backend_equivalence.py`
- Backend equivalence shape-profile companion:
  [Source-To-Intent Research Kernel Ingress Backend Equivalence Shape Profiles](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES.md)
- Backend equivalence shape-profile example:
  `examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py`
- Workload scope companion:
  [Source-To-Intent Research Kernel Ingress Workload Scope](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE.md)
- Workload scope example:
  `examples/source_to_intent_research_kernel_ingress_workload_scope.py`

## Accepted Module Shape

The v0 ingress accepts exactly:

- `import triton`
- `import triton.language as tl`
- one top-level kernel function selected by explicit `kernel_name`

The extracted function source then re-enters the existing execution-free
Triton Source Preflight and explicit Source-To-Intent Research Parser path.

Current accepted kernels are:

- `matmul_elementwise`
- `softmax_reduction`
- `matmul_reduction`
- `mvp_pipeline`

## Proof Path

The example proves all accepted module-source fixtures through:

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

The companion Kernel Ingress Rejection Coverage report proves the current
diagnostics and budget rejection surfaces are represented in one deterministic,
source-free coverage matrix.

The companion Kernel Ingress Runtime Matrix report makes the runtime side of
the four accepted cases explicit: backend sequences, terminal public outputs,
trace step counts, and runtime evidence digests are bound back to the Kernel
Ingress E2E report.

The companion Kernel Ingress Runtime Coverage Policy turns that matrix into a
minimum accepted-coverage requirement for current runtime cases, backend
sequences, terminal outputs, trace-step counts, and runtime digest fields.

The companion Kernel Ingress Runtime Backend Alignment report binds those
backend sequences to trusted Runtime Executor conformance for `linear-sim` and
`vector-sim`, without plugin discovery or device access.

The companion Kernel Ingress Backend Equivalence report executes the same
accepted Source Intent through a neutral `reference-cpu` baseline and
capability-selected trusted simulator placements, then binds the metadata-only
`RuntimeBackendEquivalenceReport` results into the Kernel Ingress proof flow.

The companion Kernel Ingress Backend Equivalence Shape Profiles report repeats
that portability check across `base` and `alternate` declared tensor shape
profiles, with reference-correctness digests for both baseline and candidate
placements.

The companion Kernel Ingress Workload Scope report binds those shape profiles
to diagnostic workload-scope review data for future performance proposals while
keeping native performance claims blocked.

The companion Kernel Ingress Proof Bundle gives reviewers a digest-only index
for the Kernel Ingress E2E, runtime-matrix, runtime-backend-equivalence,
runtime-backend-equivalence shape-profile, runtime-coverage-policy,
runtime-backend-alignment, boundary-budget, rejection-coverage, diagnostics,
conformance, and idiom-alignment artifacts.

The companion Kernel Ingress Evidence Gate validates the same artifacts and
their Proof Bundle digest bindings as CI-facing evidence.

The Source-To-Intent Research Capability Claim consumes the focused Kernel
Ingress proof and runtime artifacts to support the current bounded Universal
Compute research claim without expanding parser, backend, or performance
claims.

## Review Meaning

This is a credible research step toward the roadmap's first real Triton kernel
ingestion path. It proves that a realistic module-shaped source buffer can feed
the existing safe source-to-runtime slice, while default source parser intake
remains blocked.


## Follow-Up Evidence

- Runtime Replay Verifier Index: examples/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py

- Runtime Replay Verifier Index doc: docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX.md
