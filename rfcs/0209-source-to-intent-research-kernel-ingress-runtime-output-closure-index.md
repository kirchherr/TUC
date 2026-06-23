# RFC 0209: Source-To-Intent Research Kernel Ingress Runtime Output Closure Index

Status: Accepted

## Context

Kernel Ingress research now binds accepted Triton-module-shaped cases to
runtime matrix evidence, step traces, standard Runtime Execution Evidence
Bundles, backend equivalence, runtime coverage policy, and trusted executor
alignment. Runtime Execution Output Closure separately proves that public
runtime outputs are closed by metadata digest across Runtime Output Contract,
Runtime Public Output Bundle, Runtime Execution Receipt, and Runtime Execution
Evidence Bundle.

The missing practical bridge is to require the Kernel Ingress path to produce
that same output-closure evidence.

## Decision

Add a Runtime Output Closure Index for accepted Kernel Ingress research cases:

- `examples/source_to_intent_research_kernel_ingress_runtime_output_closure_index.py`
- `schemas/source_to_intent_research_kernel_ingress_runtime_output_closure_index_report.v0.schema.json`
- `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_output_closure_index.json`
- `tests/test_source_to_intent_research_kernel_ingress_runtime_output_closure_index.py`
- `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_OUTPUT_CLOSURE_INDEX.md`

The report records only digest bindings and counts for four accepted cases:

- `matmul_elementwise`
- `softmax_reduction`
- `matmul_reduction`
- `mvp_pipeline`

The index is bound into:

- `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- `examples/source_to_intent_research_capability_claim.py`
- `.github/workflows/ci.yml`

## Security Boundary

The slice uses already-accepted Kernel Ingress research fixtures and trusted
in-repository runtime builders. It does not serialize source text, Source
Intent payloads, tensor values, host paths, commands, backend artifacts, device
identifiers, runtime handles, URLs, generated code, timing samples, or plugin
entry points.

It does not add general Triton source ingestion, production parsing, plugin
discovery, device access, JIT execution, dynamic imports, dynamic library
loading, generated-artifact execution, network access, or subprocess execution.

## Consequences

Kernel Ingress evidence now proves not only that accepted research cases can
reach trusted runtime execution and standard Runtime Execution Evidence Bundles,
but also that their public runtime-output boundary is closed by Runtime
Execution Output Closure. This strengthens the bounded Universal Compute
research claim without claiming CUDA replacement, native performance parity, or
general source parser completeness.


## Follow-Up Evidence

- Runtime Replay Verifier Index: examples/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py
