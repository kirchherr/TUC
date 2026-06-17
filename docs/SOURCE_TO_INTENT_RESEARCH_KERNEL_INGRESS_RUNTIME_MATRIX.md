# Source-To-Intent Research Kernel Ingress Runtime Matrix

Source-To-Intent Research Kernel Ingress Runtime Matrix v0 records the runtime
evidence inventory for the accepted realistic Triton-module-shaped Kernel
Ingress research cases.

It does not add syntax, approve general Triton source ingestion, or make native
performance claims.

## Contract

- Runtime matrix contract:
  `source_to_intent_research_kernel_ingress_runtime_matrix.execution.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_runtime_matrix_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_matrix.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_runtime_matrix.py`
- Kernel Ingress source evidence:
  `examples/source_to_intent_research_kernel_ingress.py`
- Kernel Ingress Proof Bundle binding:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- Kernel Ingress Evidence Gate binding:
  `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
- Global Evidence Gate binding:
  `examples/source_to_intent_research_evidence_gate.py`
- Global Proof Bundle binding:
  `examples/source_to_intent_research_proof_bundle.py`
- CI entry: `.github/workflows/ci.yml`

## What It Records

The matrix binds accepted Kernel Ingress cases to:

- accepted case IDs and kernel names;
- operation families;
- backend sequences;
- terminal public output names;
- runtime trace step counts;
- runtime plan, execution trace, and reference correctness digests;
- the exact Kernel Ingress E2E report digest.

Current accepted sequences:

- `linear-sim->vector-sim`
- `vector-sim->vector-sim`

## Security Boundary

The matrix is metadata-only. It does not embed raw module source, extracted
kernel source, Source Intent payloads, tensor values, compiler artifacts,
backend binaries, command lines, host paths, environment variables, device
identifiers, generated code, or benchmark output.

The matrix consumes already-rendered Kernel Ingress metadata and validates the
Kernel Ingress report contract before deriving runtime inventory rows. It does
not import Triton modules, evaluate decorators, execute `@triton.jit`, access
files, access devices, load plugins, or lower source text by itself.

## Review Meaning

This artifact makes the practical runtime claim explicit:

```text
kernel ingress E2E report
    ->
runtime matrix
    ->
kernel ingress proof bundle
    ->
kernel ingress evidence gate
```

Future Kernel Ingress syntax changes must update this matrix before their
runtime behavior can count as accepted research evidence.
