# RFC 0170: Source-To-Intent Research Kernel Ingress Boundary Budget

- Status: Accepted
- Date: 2026-06-16
- Area: Frontend, Source-To-Intent, Security Evidence
- Related:
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET.md`
  - `examples/source_to_intent_research_kernel_ingress_boundary_budget.py`
  - `examples/source_to_intent_research_kernel_ingress_rejection_coverage.py`
  - `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
  - `schemas/source_to_intent_research_kernel_ingress_boundary_budget_report.v0.schema.json`
  - `tests/test_source_to_intent_research_kernel_ingress_boundary_budget.py`
  - `rfcs/0165-source-to-intent-research-kernel-ingress.md`
  - `rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md`
  - `rfcs/0171-source-to-intent-research-kernel-ingress-rejection-coverage.md`

## Context

Kernel Ingress accepts realistic Triton-module-shaped source buffers as data.
That makes resource limits part of the security boundary: module byte size,
line count, AST node count, AST depth, diagnostics case count, and report size
must remain visible and fail-closed.

## Decision

Add Source-To-Intent Research Kernel Ingress Boundary Budget v0.

The report:

- records ingress byte, line, AST-node, and AST-depth limits;
- records diagnostics case, module, and report limits;
- records accepted module observations without raw source;
- proves byte-budget, line-budget, AST-node-budget, and AST-depth-budget
  overflow reject before extraction or lowering;
- feeds those budget rejection IDs into the Kernel Ingress Rejection Coverage
  matrix;
- binds into the Kernel Ingress Proof Bundle.

The contract is:

```text
source_to_intent_research_kernel_ingress_boundary_budget.security.v0
```

## Security

The artifact is metadata-only. It must not retain raw source, extracted kernel
source, Source Intent payloads, tensor values, runtime tensors, compiler
artifacts, backend binaries, generated code, device identifiers, host paths,
command lines, environment variables, benchmark output, or exception text.

It must not import Triton modules, execute decorators, invoke JIT compilation,
discover plugins, access files by source path, or lower source text directly to
compiler artifacts.

## Consequences

Future Kernel Ingress syntax changes must keep accepted observations within
budget and add fail-closed budget evidence before the Kernel Ingress Proof
Bundle can remain valid.

This still does not prove general Triton source ingestion, production parsing,
or native performance. Those claims remain blocked.
