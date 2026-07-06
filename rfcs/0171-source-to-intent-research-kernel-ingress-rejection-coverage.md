# RFC 0171: Source-To-Intent Research Kernel Ingress Rejection Coverage

- Status: Accepted
- Date: 2026-06-16
- Area: Frontend, Source-To-Intent, Security Evidence
- Related:
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE.md`
  - `examples/source_to_intent_research_kernel_ingress_rejection_coverage.py`
  - `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
  - `schemas/source_to_intent_research_kernel_ingress_rejection_coverage_report.v0.schema.json`
  - `tests/test_source_to_intent_research_kernel_ingress_rejection_coverage.py`
  - `rfcs/0165-source-to-intent-research-kernel-ingress.md`
  - `rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md`
  - `rfcs/0170-source-to-intent-research-kernel-ingress-boundary-budget.md`

## Context

Kernel Ingress now has two rejection evidence sources:

- Diagnostics for semantic and structural module-source rejections.
- Boundary Budget for resource-exhaustion rejections.

Those reports are individually useful, but future syntax expansion needs one
auditable surface that proves the current rejection set is complete and
source-free.

## Decision

Add Source-To-Intent Research Kernel Ingress Rejection Coverage v0.

The report:

- records all current Diagnostics rejection IDs, including decorator absence,
  decorator-call, and unsupported-decorator rejections;
- records Boundary Budget byte, line, AST-node, and AST-depth overflow rejection IDs;
- creates a deterministic coverage matrix over both sources;
- binds to the Diagnostics and Boundary Budget report digests;
- binds into the Kernel Ingress Proof Bundle.

The contract is:

```text
source_to_intent_research_kernel_ingress_rejection_coverage.security.v0
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

Future Kernel Ingress syntax changes must update rejection coverage whenever
they add accepted syntax, rejected syntax, resource budgets, or diagnostics.

This still does not prove general Triton source ingestion, production parsing,
or native performance. Those claims remain blocked.
