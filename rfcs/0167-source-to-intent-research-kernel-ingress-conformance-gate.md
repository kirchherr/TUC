# RFC 0167: Source-To-Intent Research Kernel Ingress Conformance Gate

- Status: Accepted
- Date: 2026-06-16
- Area: Frontend, Source-To-Intent, Conformance Evidence
- Related:
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE.md`
  - `examples/source_to_intent_research_kernel_ingress_conformance_gate.py`
  - `examples/source_to_intent_research_evidence_gate.py`
  - `examples/source_to_intent_research_proof_bundle.py`
  - `tests/test_source_to_intent_research_kernel_ingress_conformance_gate.py`

## Context

Kernel Ingress proves that realistic Triton module-shaped source buffers can be
validated as bounded source data, reduced to one explicitly selected kernel
function, and routed through the existing Source-To-Intent research parser.

Kernel Ingress Diagnostics proves accepted and rejected module-shaped surfaces.
The remaining frontend question is whether accepted Kernel Ingress outputs are
ordinary Source Intent frontend outputs or a special path with weaker intake
rules.

## Decision

Add Source-To-Intent Research Kernel Ingress Conformance Gate v0.

The gate:

- builds the accepted Kernel Ingress results
- extracts their `source_intent.v0` plain-data payloads
- runs the reusable Source Intent Frontend Conformance path
- requires accepted matmul/elementwise and softmax/reduction cases
- requires rejected backend-hint and source-text escape cases
- emits source-free CI text evidence

## Consequences

Kernel Ingress Conformance becomes required by the Research Evidence Gate and
the Research Proof Bundle.

Future Kernel Ingress syntax changes must keep this gate passing before they
can count as accepted research scope.

## Security Notes

The gate must not:

- parse source text itself
- import modules
- evaluate decorators
- execute Triton JIT
- inspect live Python functions
- emit compiler artifacts directly from source text
- serialize raw source, Source Intent payloads, tensors, exception text, host
  paths, environment variables, device identifiers, generated code, or
  benchmark output

The only accepted lowering path remains:

```text
module source as data
    ->
Kernel Ingress
    ->
explicit research parser
    ->
source_intent.v0 plain data
    ->
Source Intent Intake
```
