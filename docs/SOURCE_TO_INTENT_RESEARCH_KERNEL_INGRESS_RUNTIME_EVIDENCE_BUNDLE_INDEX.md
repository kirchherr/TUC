# Source-To-Intent Research Kernel Ingress Runtime Evidence Bundle Index

Source-To-Intent Research Kernel Ingress Runtime Evidence Bundle Index v0
records digest-only bindings from accepted Kernel Ingress research cases to the
standard Runtime Execution Evidence Bundle contract.

It does not add syntax, approve general Triton source ingestion, execute
`@triton.jit`, expose tensor values, or make native performance claims.

## Contract

- Runtime evidence bundle index contract:
  `source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.review.v0`
- Standard runtime evidence bundle contract:
  `runtime_execution_evidence_bundle.data_only.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`
- Runtime Matrix input:
  `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
- Runtime Step Trace input:
  `examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py`
- Kernel Ingress Proof Bundle binding:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- Kernel Ingress Evidence Gate binding:
  `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- Runtime Output Closure Index consumer:
  `examples/source_to_intent_research_kernel_ingress_runtime_output_closure_index.py`
- Capability Claim binding:
  `examples/source_to_intent_research_capability_claim.py`
- Companion backend-equivalence evidence:
  `examples/source_to_intent_research_kernel_ingress_backend_equivalence.py`
- CI entry: `.github/workflows/ci.yml`

## What It Records

For each accepted Kernel Ingress case, the index builds the standard Runtime
Execution Evidence Bundle in memory and records only:

- case ID, graph name, kernel name, backend sequence, operation path, and
  terminal output names;
- runtime plan and execution trace digests;
- tensor-store, input-manifest, output-manifest, reference-correctness, and
  execution-receipt metadata digests;
- standard runtime evidence bundle metadata and report digests;
- section and item counts needed for review.

The standard bundle sections are:

- `tensor_store_evidence`
- `input_manifest`
- `output_manifest`
- `reference_correctness`
- `execution_receipt`

## Security Boundary

The index is digest-only and value-free. It does not embed raw module source,
extracted kernel source, Source Intent payloads, tensor values, generated code,
backend binaries, benchmark data, host paths, command lines, environment
variables, device identifiers, or plugin material.

The index builds evidence through trusted simulator backends and validates the
standard Runtime Execution Evidence Bundle. It does not import user modules,
execute decorators, access devices, load dynamic libraries, call subprocesses,
perform network access, or discover plugins.

## Review Meaning

This artifact connects Kernel Ingress to the same runtime evidence architecture
used by the core proof-of-execution path:

```text
kernel ingress runtime matrix
    ->
runtime step trace
    ->
standard Runtime Execution Evidence Bundles
    ->
runtime evidence bundle index
    ->
runtime output closure index
    +
backend-equivalence evidence
    ->
kernel ingress proof bundle
    ->
kernel ingress evidence gate
    ->
capability claim
```

Future accepted Kernel Ingress cases must pass the standard runtime evidence
bundle path before they can strengthen the bounded Universal Compute research
claim.
