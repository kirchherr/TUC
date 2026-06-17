# Source-To-Intent Research Kernel Ingress Conformance Gate

Source-To-Intent Research Kernel Ingress Conformance Gate v0 proves that the
accepted Kernel Ingress outputs are valid external `source_intent.v0` frontend
payloads.

It reuses the existing Source Intent Frontend Conformance path. The gate does
not parse source text itself, import modules, evaluate decorators, inspect live
functions, execute Triton JIT, or lower source directly to compiler artifacts.

## Contract

- Gate contract:
  `source_to_intent_research_kernel_ingress_conformance_gate.ci.v0`
- Example:
  `examples/source_to_intent_research_kernel_ingress_conformance_gate.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_conformance_gate.txt`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_conformance_gate.py`
- Source Intent conformance:
  `run_source_intent_frontend_conformance`
- Evidence Gate binding:
  `examples/source_to_intent_research_evidence_gate.py`
- Proof Bundle binding:
  `examples/source_to_intent_research_proof_bundle.py`
- CI entry: `.github/workflows/ci.yml`

## Required Cases

Accepted cases:

- `research_kernel_ingress_matmul_elementwise`
- `research_kernel_ingress_softmax_reduction`
- `research_kernel_ingress_matmul_reduction`
- `research_kernel_ingress_mvp_pipeline`

Rejected conformance cases:

- `reject_kernel_ingress_backend_hint_escape`
- `reject_kernel_ingress_source_text_escape`

The rejected cases are Source Intent payload checks. They prove Kernel Ingress
does not get a privileged bypass around the existing frontend intake boundary.

## Security Boundary

Kernel Ingress Conformance consumes already produced Kernel Ingress results and
then runs reusable Source Intent Frontend Conformance on their plain-data
payloads.

The report is source-free and must not contain raw module source, extracted
kernel source, Source Intent payloads, exception text, tensors, compiler
artifacts, host paths, environment variables, device identifiers, generated
code, or benchmark output.

## Review Meaning

This gate proves that realistic Triton module-shaped input still lands on the
same external frontend contract as every other Source Intent producer. Future
Kernel Ingress syntax can expand only if this conformance gate remains passing
and source-free.
