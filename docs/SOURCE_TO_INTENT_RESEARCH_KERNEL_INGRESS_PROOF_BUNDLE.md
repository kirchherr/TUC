# Source-To-Intent Research Kernel Ingress Proof Bundle

Source-To-Intent Research Kernel Ingress Proof Bundle v0 is the digest-only
review entry point for the realistic Triton-module-shaped Kernel Ingress
research slice.

It does not approve general Triton source ingestion, production parsing, or
native performance claims.

## Contract

- Bundle contract:
  `source_to_intent_research_kernel_ingress_proof_bundle.review.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_proof_bundle_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_proof_bundle.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_proof_bundle.py`
- Evidence Gate binding: `examples/source_to_intent_research_evidence_gate.py`
- Global Proof Bundle binding: `examples/source_to_intent_research_proof_bundle.py`
- CI entry: `.github/workflows/ci.yml`

## What It Bundles

The bundle records SHA-256 digests for:

- Source-To-Intent Research Kernel Ingress
- Source-To-Intent Research Kernel Ingress Boundary Budget
- Source-To-Intent Research Kernel Ingress Rejection Coverage
- Source-To-Intent Research Kernel Ingress Diagnostics
- Source-To-Intent Research Kernel Ingress Conformance Gate
- Source-To-Intent Research Kernel Ingress Idiom Alignment

It validates the structured JSON reports and source-free text gate before
emitting the bundle.

Kernel Ingress Boundary Budget artifact path:
`examples/source_to_intent_research_kernel_ingress_boundary_budget.py`

Kernel Ingress Rejection Coverage artifact path:
`examples/source_to_intent_research_kernel_ingress_rejection_coverage.py`

## Blocked Claims

The bundle explicitly keeps these claims blocked:

- `general_triton_source_ingestion`
- `native_performance_claim`
- `production_parser`

## Security Boundary

The bundle is digest-only and source-free. It does not embed raw module source,
extracted kernel source, Source Intent payloads, tensor values, compiler
artifacts, runtime plans, backend decisions, host paths, command lines,
environment variables, device identifiers, exception text, generated code, or
benchmark output.

It does not parse source text, import Triton modules, evaluate decorators,
execute `@triton.jit`, access files, access devices, load plugins, or generate
artifacts.

## Review Meaning

This bundle gives reviewers one small artifact for the Kernel Ingress claim:

```text
kernel ingress
kernel ingress boundary budget
kernel ingress rejection coverage
kernel ingress diagnostics
kernel ingress conformance gate
kernel ingress idiom alignment
    ->
digest-only kernel ingress proof bundle
```

Future Kernel Ingress syntax must update the underlying evidence before this
bundle can remain valid.
