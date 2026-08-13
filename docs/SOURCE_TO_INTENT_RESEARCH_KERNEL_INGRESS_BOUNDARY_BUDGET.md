# Source-To-Intent Research Kernel Ingress Boundary Budget

Source-To-Intent Research Kernel Ingress Boundary Budget v0 records the
resource limits and fail-closed behavior for realistic Triton-module-shaped
Kernel Ingress inputs.

It does not add new syntax, parse source into compiler artifacts, or approve
general Triton ingestion.

## Contract

- Boundary contract:
  `source_to_intent_research_kernel_ingress_boundary_budget.security.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_boundary_budget_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_kernel_ingress_boundary_budget.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_boundary_budget.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_boundary_budget.py`
- Kernel Ingress Proof Bundle binding:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- Rejection coverage companion:
  `examples/source_to_intent_research_kernel_ingress_rejection_coverage.py`
- CI entry: `.github/workflows/ci.yml`

## What It Proves

The report proves:

- accepted module-shaped fixtures stay within byte, line, AST-node, and
  AST-depth limits;
- the accepted observation set covers `matmul_elementwise`,
  `softmax_reduction`, `matmul_reduction`, `softmax_elementwise`, and
  `mvp_pipeline`;
- module byte-budget overflow is rejected before extraction or lowering;
- module line-budget overflow is rejected before extraction or lowering;
- module AST-node-budget overflow is rejected before extraction or lowering;
- module AST-depth-budget overflow is rejected before extraction or lowering;
- diagnostics case, module, and report budgets are visible to reviewers;
- raw source text, Source Intent payloads, tensor values, compiler artifacts,
  backend artifacts, and runtime values remain omitted.

## Security Boundary

Kernel Ingress treats module source as untrusted data. This boundary budget
artifact does not import modules, evaluate decorators, execute `@triton.jit`,
inspect live Python functions, access files, access devices, load plugins, run
subprocesses, or emit generated code.

The report keeps parser status as `research_explicit_only` and default parser
status as `default_parser_blocked`.

## Review Meaning

This artifact is the resource-exhaustion guard for the Kernel Ingress research
slice. Future ingress syntax must keep accepted observations under budget and
add fail-closed budget evidence before it can count as accepted research scope.

The companion Kernel Ingress Rejection Coverage report binds these budget
rejections together with Diagnostics rejection IDs before the Kernel Ingress
Proof Bundle can pass.
