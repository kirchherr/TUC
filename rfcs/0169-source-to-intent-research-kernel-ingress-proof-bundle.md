# RFC 0169: Source-To-Intent Research Kernel Ingress Proof Bundle

- Status: Accepted
- Date: 2026-06-16
- Area: Frontend, Source-To-Intent, Review Evidence
- Related:
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md`
  - `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`
  - `examples/source_to_intent_research_kernel_ingress_boundary_budget.py`
  - `examples/source_to_intent_research_kernel_ingress_rejection_coverage.py`
  - `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
  - `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
  - `examples/source_to_intent_research_evidence_gate.py`
  - `examples/source_to_intent_research_proof_bundle.py`
  - `schemas/source_to_intent_research_kernel_ingress_proof_bundle_report.v0.schema.json`
  - `tests/test_source_to_intent_research_kernel_ingress_proof_bundle.py`
  - `rfcs/0165-source-to-intent-research-kernel-ingress.md`
  - `rfcs/0166-source-to-intent-research-kernel-ingress-diagnostics.md`
  - `rfcs/0167-source-to-intent-research-kernel-ingress-conformance-gate.md`
  - `rfcs/0168-source-to-intent-research-kernel-ingress-idiom-alignment.md`
  - `rfcs/0170-source-to-intent-research-kernel-ingress-boundary-budget.md`
  - `rfcs/0171-source-to-intent-research-kernel-ingress-rejection-coverage.md`
  - `rfcs/0172-source-to-intent-research-kernel-ingress-evidence-gate.md`
  - `rfcs/0173-source-to-intent-research-kernel-ingress-runtime-matrix.md`
  - `rfcs/0174-source-to-intent-research-kernel-ingress-runtime-coverage-policy.md`
  - `rfcs/0175-source-to-intent-research-kernel-ingress-runtime-backend-alignment.md`

## Context

Kernel Ingress now has focused proof artifacts: runtime E2E evidence,
runtime-matrix evidence, runtime-coverage-policy evidence,
runtime-backend-alignment evidence, boundary-budget evidence,
rejection-coverage evidence, source-free diagnostics, frontend conformance, and
idiom alignment.

Each artifact is useful alone, but reviewers need one small digest-only index
for the Kernel Ingress claim without reading the entire Source-To-Intent
Research Proof Bundle.

## Decision

Add Source-To-Intent Research Kernel Ingress Proof Bundle v0.

The bundle:

- records digests for the Kernel Ingress proof artifacts;
- validates each artifact before emitting its own report;
- binds into the Source-To-Intent Research Evidence Gate;
- binds into the focused Kernel Ingress Evidence Gate;
- binds into the global Source-To-Intent Research Proof Bundle;
- remains digest-only and source-free.

The contract is:

```text
source_to_intent_research_kernel_ingress_proof_bundle.review.v0
```

## Security

The bundle must not retain raw module source, extracted kernel source, Source
Intent payloads, tensor values, runtime tensors, compiler artifacts, backend
binaries, generated code, device identifiers, host paths, command lines,
environment variables, benchmark output, or exception text.

It must not import Triton modules, execute decorators, invoke JIT compilation,
discover plugins, access files by source path, or lower source text directly to
compiler artifacts.

## Consequences

The Kernel Ingress research claim becomes easier to audit without weakening any
boundary. Future Kernel Ingress syntax changes must update E2E,
runtime-matrix, runtime-coverage-policy, runtime-backend-alignment,
boundary-budget, rejection-coverage, diagnostics, conformance, idiom-alignment,
this bundle, the focused Kernel Ingress Evidence Gate, the global Evidence
Gate, and the global Proof Bundle together.

This still does not prove general Triton source ingestion, production parsing,
or native performance. Those claims remain blocked.
