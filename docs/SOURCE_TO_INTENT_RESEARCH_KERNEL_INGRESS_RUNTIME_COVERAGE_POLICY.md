# Source-To-Intent Research Kernel Ingress Runtime Coverage Policy

Source-To-Intent Research Kernel Ingress Runtime Coverage Policy v0 records the
minimum runtime coverage that accepted Kernel Ingress research cases must keep.

It does not add syntax, approve general Triton source ingestion, or make native
performance claims.

## Contract

- Policy contract:
  `source_to_intent_research_kernel_ingress_runtime_coverage_policy.review.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_runtime_coverage_policy_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_coverage_policy.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`
- Runtime Matrix input:
  `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
- Runtime Step Trace companion:
  `examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py`
- Runtime Step Trace docs:
  [Source-To-Intent Research Kernel Ingress Runtime Step Trace](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE.md)
- Runtime Evidence Bundle Index companion:
  `examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`
- Runtime Evidence Bundle Index docs:
  [Source-To-Intent Research Kernel Ingress Runtime Evidence Bundle Index](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX.md)
- Runtime Backend Alignment binding:
  `examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`
- Runtime Backend Alignment docs:
  [Source-To-Intent Research Kernel Ingress Runtime Backend Alignment](SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT.md)
- Kernel Ingress Proof Bundle binding:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- Kernel Ingress Evidence Gate binding:
  `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- Global Evidence Gate binding:
  `examples/source_to_intent_research_evidence_gate.py`
- Global Proof Bundle binding:
  `examples/source_to_intent_research_proof_bundle.py`
- CI entry: `.github/workflows/ci.yml`

## Required Coverage

The policy currently requires:

- four accepted Kernel Ingress runtime cases;
- operation-family coverage for `elementwise`, `matmul`, `reduction`, and
  `softmax`;
- backend sequences `linear-sim->vector-sim`, `vector-sim->vector-sim`, and
  `linear-sim->vector-sim->vector-sim->vector-sim`;
- terminal outputs `activated`, `row_sum`, `column_sum`, and `stable`;
- trace step counts `2`, `2`, `2`, and `4` for the current accepted cases;
- `runtime_plan_digest`, `execution_trace_digest`, and
  `reference_correctness_digest` for each case.

## Security Boundary

The policy is metadata-only. It consumes the already-rendered Runtime Matrix,
validates its contract, and records coverage requirements plus observed
coverage. It does not embed raw module source, extracted kernel source, Source
Intent payloads, tensor values, compiler artifacts, backend binaries, command
lines, host paths, environment variables, device identifiers, generated code,
or benchmark output.

It does not import Triton modules, evaluate decorators, execute `@triton.jit`,
access files, access devices, load plugins, run subprocesses, or lower source
text by itself.

## Review Meaning

This artifact turns the Runtime Matrix into a guarded obligation:

```text
kernel ingress runtime matrix
    ->
runtime step trace
    ->
runtime evidence bundle index
    ->
runtime coverage policy
    ->
runtime backend alignment
    ->
kernel ingress proof bundle
    ->
kernel ingress evidence gate
```

Future Kernel Ingress syntax or runtime behavior can expand only after this
policy is consciously updated and the downstream bundles and gates pass.
