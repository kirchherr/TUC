# Source-To-Intent Research Kernel Ingress Rejection Coverage

Source-To-Intent Research Kernel Ingress Rejection Coverage v0 records the
current fail-closed rejection surface for realistic Triton-module-shaped Kernel
Ingress inputs.

It does not add new syntax, parse source into compiler artifacts, or approve
general Triton ingestion.

## Contract

- Coverage contract:
  `source_to_intent_research_kernel_ingress_rejection_coverage.security.v0`
- Report schema:
  `schemas/source_to_intent_research_kernel_ingress_rejection_coverage_report.v0.schema.json`
- Example:
  `examples/source_to_intent_research_kernel_ingress_rejection_coverage.py`
- Golden:
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_rejection_coverage.json`
- Tests:
  `tests/test_source_to_intent_research_kernel_ingress_rejection_coverage.py`
- Kernel Ingress Proof Bundle binding:
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
- CI entry: `.github/workflows/ci.yml`

## What It Proves

The report proves:

- Kernel Ingress Diagnostics covers unsupported imports, import-from
  statements, multiple kernel functions, top-level side effects, and target
  kernel-name mismatches;
- Kernel Ingress Boundary Budget covers module byte-budget, line-budget,
  AST-node-budget, and AST-depth-budget overflow rejections;
- all current rejection reasons are represented in one deterministic coverage
  matrix;
- the coverage matrix binds to the exact diagnostics and boundary-budget report
  digests;
- raw source text, Source Intent payloads, tensor values, compiler artifacts,
  backend artifacts, and runtime values remain omitted.

## Security Boundary

The artifact is metadata-only and source-free. It does not import modules,
evaluate decorators, execute `@triton.jit`, inspect live Python functions,
access files, access devices, load plugins, run subprocesses, or emit generated
code.

The report keeps parser status as `research_explicit_only` and default parser
status as `default_parser_blocked`.

## Review Meaning

This artifact is the rejection-surface audit for the Kernel Ingress research
slice. Future ingress syntax must extend diagnostics, boundary budgets, or both
before the Kernel Ingress Proof Bundle can remain valid.
