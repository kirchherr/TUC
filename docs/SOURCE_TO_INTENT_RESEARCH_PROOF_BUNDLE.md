# Source-To-Intent Research Proof Bundle

Source-To-Intent Research Proof Bundle v0 is the digest-only review entry point
for the current Source-to-Intent research proof chain.

It does not approve production parsing, general Triton source ingestion, or
native performance claims.

## Contract

- Bundle contract: `source_to_intent_research_proof_bundle.review.v0`
- Report schema version:
  `tuc.source_to_intent_research_proof_bundle_report.v0`
- Report schema:
  `schemas/source_to_intent_research_proof_bundle_report.v0.schema.json`
- Example: `examples/source_to_intent_research_proof_bundle.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_proof_bundle.json`
- Tests: `tests/test_source_to_intent_research_proof_bundle.py`
- CI entry: `.github/workflows/ci.yml`

## What It Bundles

The bundle records SHA-256 digests for:

- Source-To-Intent Research Readiness
- Source-To-Intent Research Parser Conformance Gate
- Source-To-Intent Research Diagnostics
- Source-To-Intent Research Preflight Bridge
- Source-To-Intent Research Execution Bridge
- Source-To-Intent Research Idiom Alignment
- Source-To-Intent Research Source Runtime Smoke
- Source-To-Intent Research Kernel Ingress
- Source-To-Intent Research Kernel Ingress Conformance Gate
- Source-To-Intent Research Kernel Ingress Diagnostics
- Source-To-Intent Research Evidence Gate

Kernel Ingress artifact path:
`examples/source_to_intent_research_kernel_ingress.py`

Kernel Ingress Conformance Gate artifact path:
`examples/source_to_intent_research_kernel_ingress_conformance_gate.py`

Kernel Ingress Diagnostics artifact path:
`examples/source_to_intent_research_kernel_ingress_diagnostics.py`

The bundle claim is:

```text
safe_source_to_runtime_research_slice
```

## Blocked Claims

The bundle explicitly keeps these claims blocked:

- `general_triton_source_ingestion`
- `native_performance_claim`
- `production_parser`

## Security Boundary

The bundle is digest-only and source-free. It does not embed raw source text,
Source Intent payloads, tensor values, compiler artifacts, runtime plans,
backend decisions, host paths, command lines, environment variables, device
identifiers, exception text, generated code, or benchmark output.

It validates the structured bridge reports and checks that the Research
Evidence Gate contains the expected digests before the bundle can pass.

## Review Meaning

This bundle gives reviewers one stable artifact for the current research proof:

```text
readiness
conformance
diagnostics
preflight bridge
execution bridge
idiom alignment
source runtime smoke
kernel ingress
kernel ingress conformance gate
kernel ingress diagnostics
evidence gate
    ->
digest-only proof bundle
```

Future parser-scope changes must update the underlying evidence before the
bundle can remain valid.
