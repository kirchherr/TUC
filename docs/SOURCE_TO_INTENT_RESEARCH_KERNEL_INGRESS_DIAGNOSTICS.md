# Source-To-Intent Research Kernel Ingress Diagnostics

Source-To-Intent Research Kernel Ingress Diagnostics v0 records source-free
accepted and rejected evidence for the explicit Kernel Ingress path.

It exists because Kernel Ingress widened the input shape from function snippets
to realistic Triton module-shaped source buffers. That new source boundary needs
deterministic rejection evidence before any future syntax expansion can count as
accepted research scope.

## Contract

- Diagnostics contract:
  `source_to_intent_research_kernel_ingress_diagnostics.execution_free.v0`
- Ingress contract:
  `source_to_intent_research_kernel_ingress.execution_free.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_diagnostics_report.v0.schema.json`
- Frontend API:
  `src/tuc/frontend/source_to_intent_research_kernel_ingress_diagnostics.py`
- Example:
  `examples/source_to_intent_research_kernel_ingress_diagnostics.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_diagnostics_report.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_diagnostics.py`
- Gate binding:
  `examples/source_to_intent_research_evidence_gate.py`
- Proof bundle binding:
  `examples/source_to_intent_research_proof_bundle.py`
- CI entry: `.github/workflows/ci.yml`

## Accepted Cases

- `accepted_module_matmul_elementwise`
- `accepted_module_softmax_reduction`
- `accepted_module_matmul_reduction`
- `accepted_module_softmax_elementwise`
- `accepted_module_mvp_pipeline`

Accepted cases record module digest, operation families, and Kernel Ingress
report digest. They do not serialize module source, extracted kernel source, or
Source Intent payloads.

## Rejected Cases

The v0 diagnostics report requires these source-free rejection reason IDs:

- `unsupported_import`
- `import_from_statement`
- `missing_triton_jit_decorator`
- `decorator_call`
- `unsupported_decorator`
- `multiple_kernel_functions`
- `top_level_side_effect`
- `kernel_name_mismatch`

The report never emits exception text. It checks exception text internally only
to map an observed rejection to the expected stable reason ID.

## Security Boundary

Diagnostics run Kernel Ingress as data-only validation. They do not import
Python modules, evaluate decorators, execute `@triton.jit`, read source files by
path, inspect live Python functions, access devices, discover plugins, emit
generated code, or lower source text directly to compiler artifacts.

The report is metadata-only and omits raw source text, source snippets, Source
Intent payloads, tensor values, compiler artifacts, host paths, command lines,
environment variables, device identifiers, generated code, exception text, and
benchmark output.

## Review Meaning

Kernel Ingress Diagnostics is the fail-closed companion to Kernel Ingress. It
lets reviewers see which realistic module forms are accepted, which risky
module surfaces are rejected, and whether that boundary stays stable in CI.
