# Source-To-Intent Research Kernel Ingress Runtime Step Trace

Source-To-Intent Research Kernel Ingress Runtime Step Trace v0 records the
operation-level execution path for each accepted Kernel Ingress research case.

It does not add syntax, approve general Triton source ingestion, execute
`@triton.jit`, or make native performance claims.

## Contract

- Runtime step trace contract:
  `source_to_intent_research_kernel_ingress_runtime_step_trace.execution.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_runtime_step_trace_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_step_trace.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_runtime_step_trace.py`
- Kernel Ingress source evidence:
  `examples/source_to_intent_research_kernel_ingress.py`
- Runtime Matrix binding:
  `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
- Kernel Ingress Proof Bundle binding:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- Kernel Ingress Evidence Gate binding:
  `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- Capability Claim binding:
  `examples/source_to_intent_research_capability_claim.py`
- CI entry: `.github/workflows/ci.yml`

## What It Records

The step trace binds accepted Kernel Ingress cases to:

- accepted case IDs and kernel names;
- planned backend sequence and executor backend sequence;
- operation path in runtime order;
- public input and output tensor names;
- output dtype and shape metadata;
- runtime plan and execution trace digests;
- the exact Kernel Ingress and Runtime Matrix report digests.

Current accepted step paths:

- `matmul -> elementwise`
- `softmax -> reduction`
- `matmul -> reduction`
- `matmul -> softmax -> reduction -> elementwise`

## Security Boundary

The trace is metadata-only. It omits raw module source, extracted kernel source,
Source Intent payloads, tensor values, generated code, backend binaries,
benchmark data, host paths, command lines, environment variables, device
identifiers, and plugin material.

The trace is built through trusted simulator backends and the trusted Runtime
Executor registry. It does not import user modules, execute decorators, access
devices, load dynamic libraries, call subprocesses, perform network access, or
discover plugins.

## Review Meaning

This artifact turns the runtime matrix from inventory into inspectable execution
order:

```text
kernel ingress E2E report
    ->
runtime matrix
    ->
runtime step trace
    ->
runtime coverage policy
    ->
kernel ingress proof bundle
    ->
kernel ingress evidence gate
    ->
capability claim
```

Future accepted Kernel Ingress cases must update this trace before their runtime
behavior can count as capability evidence.
