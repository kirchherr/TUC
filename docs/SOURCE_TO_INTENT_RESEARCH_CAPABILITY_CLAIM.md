# Source-To-Intent Research Capability Claim

Source-To-Intent Research Capability Claim v0 is the digest-only review summary
for the current bounded Universal Compute research slice.

It turns the existing evidence chain into one explicit claim boundary: accepted
Source-to-Intent research inputs can reach capability-selected trusted runtime
execution for the MVP operation families, while production parsing, native
performance, hardware certification, arbitrary backend execution, and vendor
compiler replacement claims remain blocked.

## Contract

- Claim contract:
  `source_to_intent_research_capability_claim.review.v0`
- Report schema:
  `schemas/source_to_intent_research_capability_claim_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_capability_claim.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_capability_claim.json`
- Tests:
  `tests/test_source_to_intent_research_capability_claim.py`
- CI entry: `.github/workflows/ci.yml`

## Supported Current Claim

The report supports only:

```text
bounded_universal_compute_research_slice
```

The claim status is:

```text
supported_for_current_research_scope
```

The claim scope is:

```text
accepted_source_to_intent_kernel_ingress_mvp_pipeline
```

## Evidence Inputs

The claim report records SHA-256 digests for:

- Source-To-Intent Research Proof Bundle
- Source-To-Intent Research Evidence Gate
- Source-To-Intent Research Kernel Ingress Proof Bundle
- Source-To-Intent Research Kernel Ingress Evidence Gate
- Source-To-Intent Research Kernel Ingress Runtime Matrix
- Source-To-Intent Research Kernel Ingress Runtime Coverage Policy
- Source-To-Intent Research Kernel Ingress Runtime Backend Alignment

It validates structured JSON contracts before accepting the digest, and checks
the text gates for required pass/fail bindings.

## Acceptance Checks

The report passes only when:

- the global proof bundle passes;
- the global evidence gate passes;
- the Kernel Ingress proof bundle passes;
- the Kernel Ingress evidence gate passes;
- the runtime matrix contains the combined `mvp_pipeline` case;
- the runtime coverage policy requires exact trace counts, including four
  steps for `mvp_pipeline`;
- runtime backend alignment uses only trusted executor backends.

The combined pipeline path is:

```text
matmul -> softmax -> reduction -> elementwise
```

The accepted trusted runtime backends are:

```text
linear-sim
vector-sim
```

## Blocked Claims

The report explicitly keeps these claims blocked:

- `arbitrary_backend_execution`
- `general_triton_source_ingestion`
- `hardware_certification`
- `native_performance_claim`
- `production_parser`
- `vendor_compiler_replacement`

## Security Boundary

The report is digest-only and source-free. It does not embed raw module source,
extracted kernel source, Source Intent payloads, tensor values, compiler
artifacts, runtime plans, backend decisions, host paths, command lines,
environment variables, device identifiers, exception text, generated code, or
benchmark output.

It does not parse source text, import Triton modules, evaluate decorators,
execute `@triton.jit`, access files, access devices, load plugins, or generate
artifacts.

## Review Meaning

This report is the current high-level research answer:

```text
global proof bundle
global evidence gate
kernel ingress proof bundle
kernel ingress evidence gate
runtime matrix
runtime coverage policy
runtime backend alignment
    ->
bounded Universal Compute research capability claim
```

Future parser, runtime, backend, or performance claims must add evidence below
this report before the supported claim scope can expand.
