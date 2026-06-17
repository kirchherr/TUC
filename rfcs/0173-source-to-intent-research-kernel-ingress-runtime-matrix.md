# RFC 0173: Source-To-Intent Research Kernel Ingress Runtime Matrix

- Status: Accepted
- Date: 2026-06-17
- Owners: TUC maintainers
- Related artifacts:
  - `examples/source_to_intent_research_kernel_ingress.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
  - `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
  - `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
  - `schemas/source_to_intent_research_kernel_ingress_runtime_matrix_report.v0.schema.json`
  - `tests/test_source_to_intent_research_kernel_ingress_runtime_matrix.py`
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX.md`

## Context

Kernel Ingress already proves that two realistic Triton-module-shaped source
buffers can pass bounded module validation, extraction, Source Intent intake,
runtime planning, runtime execution, and reference correctness.

That evidence was present in the E2E report, but reviewers still had to inspect
case rows to understand the runtime coverage. TUC needs a small source-free
artifact that answers one practical question directly: which accepted Kernel
Ingress cases are bound to runtime plans, backend sequences, execution traces,
and correctness digests?

## Decision

Add Source-To-Intent Research Kernel Ingress Runtime Matrix v0.

The matrix:

- derives from the Kernel Ingress E2E report;
- validates the Kernel Ingress E2E contract before summarizing it;
- records accepted case IDs, kernel names, operation families, backend
  sequences, terminal output names, trace step counts, and runtime evidence
  digests;
- binds the exact Kernel Ingress E2E report digest;
- remains metadata-only and source-free;
- is required by the Kernel Ingress Proof Bundle;
- is required by the focused Kernel Ingress Evidence Gate.

## Contract

```text
source_to_intent_research_kernel_ingress_runtime_matrix.execution.v0
```

Schema:

```text
schemas/source_to_intent_research_kernel_ingress_runtime_matrix_report.v0.schema.json
```

## Security

The matrix does not parse source text, execute source, evaluate decorators,
import Triton, expose Source Intent payloads, expose tensor values, emit backend
code, run subprocesses, access files, access devices, or load plugins.

The artifact forbids known source and value fragments in its rendered output.
It is a derived metadata artifact over already accepted evidence.

## Consequences

Kernel Ingress runtime coverage is easier to audit. Future source-shape growth
must update E2E evidence, the runtime matrix, the Kernel Ingress Proof Bundle,
the focused Kernel Ingress Evidence Gate, the global Evidence Gate, and the
global Proof Bundle before it can count as accepted research scope.
