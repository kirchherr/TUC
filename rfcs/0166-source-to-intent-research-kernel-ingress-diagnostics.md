# RFC 0166: Source-To-Intent Research Kernel Ingress Diagnostics

- Status: Accepted
- Date: 2026-06-16
- Area: Frontend, Source-To-Intent, Security Evidence
- Related:
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS.md`
  - `examples/source_to_intent_research_kernel_ingress_diagnostics.py`
  - `examples/source_to_intent_research_evidence_gate.py`
  - `examples/source_to_intent_research_proof_bundle.py`
  - `schemas/source_to_intent_research_kernel_ingress_diagnostics_report.v0.schema.json`
  - `tests/test_source_to_intent_research_kernel_ingress_diagnostics.py`

## Context

RFC 0165 added Source-To-Intent Research Kernel Ingress. It proved that a
realistic Triton module-shaped source buffer can be validated as data, reduced
to one explicitly selected kernel function, and run through the existing
Source-To-Intent research path.

That new input shape also creates a new review obligation: the project must
show which module surfaces are accepted and which are rejected before future
syntax expansion can count as credible research evidence.

## Decision

Add Source-To-Intent Research Kernel Ingress Diagnostics v0.

The diagnostics report records source-free evidence for:

- accepted module-shaped `matmul -> elementwise`
- accepted module-shaped `softmax -> reduction`
- accepted module-shaped `matmul -> reduction`
- accepted module-shaped `softmax -> elementwise`
- accepted module-shaped MVP pipeline
- unsupported imports
- import-from statements
- imports after the selected kernel function
- missing `@triton.jit` decorators
- decorator calls
- unsupported decorators
- multiple top-level kernel functions
- top-level side effects
- kernel name mismatch

The report uses stable rejection reason IDs and never emits raw module source,
raw extracted kernel source, exception text, Source Intent payloads, tensors,
compiler artifacts, generated code, host paths, environment variables, device
identifiers, or benchmark output.

## Consequences

Kernel Ingress Diagnostics becomes a required artifact for the Research
Evidence Gate and the Research Proof Bundle.

Future Kernel Ingress syntax changes must update:

- accepted/rejected diagnostic cases
- report schema
- golden evidence
- Evidence Gate binding
- Proof Bundle binding
- documentation and RFC context

## Security Notes

The diagnostics runner executes only bounded module-source validation and the
existing explicit Kernel Ingress path.

It must not:

- import Python modules
- evaluate decorators
- execute Triton JIT
- inspect live Python functions
- read source files by path
- access devices
- discover plugins
- run subprocesses
- emit compiler artifacts directly from source text

Source text can influence compiler artifacts only after Kernel Ingress extracts
one function and the existing Source-To-Intent Research Parser emits validated
`source_intent.v0` plain data for Source Intent Intake.
