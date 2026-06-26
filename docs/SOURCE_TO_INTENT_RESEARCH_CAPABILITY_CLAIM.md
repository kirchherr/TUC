# Source-To-Intent Research Capability Claim

Source-To-Intent Research Capability Claim v0 is the digest-only review summary
for the current bounded Universal Compute research slice.

It turns the existing evidence chain into one explicit claim boundary: accepted
Source-to-Intent research inputs can reach capability-selected trusted runtime
execution for the MVP operation families and preserve public outputs against a
neutral `reference-cpu` baseline, while production parsing, native performance,
hardware certification, arbitrary backend execution, and vendor compiler
replacement claims remain blocked.

## Contract

- Claim contract:
  `source_to_intent_research_capability_claim.review.v0`
- Report schema:
  `schemas/source_to_intent_research_capability_claim_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_capability_claim.py`
- CI gate:
  `examples/source_to_intent_research_capability_claim_gate.py`
- Gate docs:
  [Source-To-Intent Research Capability Claim Gate](SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE.md)
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
- Source-To-Intent Research Kernel Ingress Runtime Step Trace
- Source-To-Intent Research Kernel Ingress Runtime Evidence Bundle Index
- Source-To-Intent Research Kernel Ingress Runtime Output Closure Index
- Source-To-Intent Research Kernel Ingress Runtime Replay Verifier Index
- Source-To-Intent Research Kernel Ingress Backend Equivalence
- Source-To-Intent Research Kernel Ingress Backend Equivalence Shape Profiles
- Source-To-Intent Research Kernel Ingress Runtime Coverage Policy
- Source-To-Intent Research Kernel Ingress Runtime Backend Alignment

It validates structured JSON contracts before accepting the digest, and checks
the text gates for required pass/fail bindings.

Source-To-Intent Research Proof Bundle artifact path:
`examples/source_to_intent_research_proof_bundle.py`

Source-To-Intent Research Evidence Gate artifact path:
`examples/source_to_intent_research_evidence_gate.py`

Kernel Ingress Proof Bundle artifact path:
`examples/source_to_intent_research_kernel_ingress_proof_bundle.py`

Kernel Ingress Evidence Gate artifact path:
`examples/source_to_intent_research_kernel_ingress_evidence_gate.py`

Kernel Ingress Runtime Matrix artifact path:
`examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`

Kernel Ingress Runtime Step Trace artifact path:
`examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py`

Kernel Ingress Runtime Evidence Bundle Index artifact path:
`examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`

Kernel Ingress Runtime Output Closure Index artifact path:
`examples/source_to_intent_research_kernel_ingress_runtime_output_closure_index.py`

Kernel Ingress Runtime Replay Verifier Index artifact path:
`examples/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py`

Kernel Ingress Backend Equivalence artifact path:
`examples/source_to_intent_research_kernel_ingress_backend_equivalence.py`

Kernel Ingress Backend Equivalence Shape Profiles artifact path:
`examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py`

Kernel Ingress Runtime Coverage Policy artifact path:
`examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`

Kernel Ingress Runtime Backend Alignment artifact path:
`examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`

## Acceptance Checks

The report passes only when:

- the global proof bundle passes;
- the global evidence gate passes;
- the Kernel Ingress proof bundle passes;
- the Kernel Ingress evidence gate passes;
- the runtime matrix contains the combined `mvp_pipeline` case;
- the runtime step trace binds the combined `mvp_pipeline` operation path;
- the runtime evidence bundle index binds standard execution evidence sections
  for the combined `mvp_pipeline` case;
- the runtime output closure index closes public output metadata for the
  combined `mvp_pipeline` case;
- the runtime replay verifier index replay-checks serialized runtime evidence
  and output closure reports for the combined `mvp_pipeline` case;
- backend equivalence preserves terminal output metadata between a
  `reference-cpu` baseline and capability-selected trusted simulator
  placement for the combined `mvp_pipeline` case;
- backend equivalence shape profiles preserve terminal output metadata and
  reference correctness across `base` and `alternate` declared tensor shape
  profiles for the combined `mvp_pipeline` case;
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

The baseline runtime backend for portability comparison is:

```text
reference-cpu
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
runtime step trace
runtime evidence bundle index
runtime output closure index
runtime replay verifier index
backend equivalence
backend equivalence shape profiles
runtime coverage policy
runtime backend alignment
    ->
bounded Universal Compute research capability claim
    ->
capability claim gate
```

Future parser, runtime, backend, or performance claims must add evidence below
this report before the supported claim scope can expand, and must update the
gate before the expanded claim can merge.
