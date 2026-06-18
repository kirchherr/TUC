# RFC 0172: Source-To-Intent Research Kernel Ingress Evidence Gate

- Status: Accepted
- Date: 2026-06-17
- Area: Frontend, Source-To-Intent, CI Evidence
- Related:
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md`
  - `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`
  - `examples/source_to_intent_research_kernel_ingress_backend_equivalence.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`
  - `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
  - `examples/source_to_intent_research_evidence_gate.py`
  - `examples/source_to_intent_research_proof_bundle.py`
  - `tests/test_source_to_intent_research_kernel_ingress_evidence_gate.py`
  - `rfcs/0165-source-to-intent-research-kernel-ingress.md`
  - `rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md`
  - `rfcs/0171-source-to-intent-research-kernel-ingress-rejection-coverage.md`
  - `rfcs/0173-source-to-intent-research-kernel-ingress-runtime-matrix.md`
  - `rfcs/0180-source-to-intent-research-kernel-ingress-runtime-step-trace.md`
  - `rfcs/0181-source-to-intent-research-kernel-ingress-runtime-evidence-bundle-index.md`
  - `rfcs/0182-source-to-intent-research-kernel-ingress-backend-equivalence.md`
  - `rfcs/0174-source-to-intent-research-kernel-ingress-runtime-coverage-policy.md`
  - `rfcs/0175-source-to-intent-research-kernel-ingress-runtime-backend-alignment.md`

## Context

Kernel Ingress now has separate E2E, runtime-matrix,
runtime-backend-equivalence, runtime-coverage-policy,
runtime-backend-alignment, boundary-budget, rejection-coverage, diagnostics,
conformance, idiom-alignment, and proof-bundle artifacts.

The global Source-To-Intent Research Evidence Gate can bind those artifacts, but
the realistic module-ingress slice benefits from a focused gate that verifies
the exact same Kernel Ingress artifact set before the global gate accepts it.

## Decision

Add Source-To-Intent Research Kernel Ingress Evidence Gate v0.

The gate:

- validates Kernel Ingress E2E evidence;
- validates Runtime Matrix evidence;
- validates Runtime Backend Equivalence evidence;
- validates Runtime Coverage Policy evidence;
- validates Runtime Backend Alignment evidence;
- validates Boundary Budget evidence;
- validates Rejection Coverage evidence;
- validates Diagnostics evidence;
- validates Conformance Gate evidence;
- validates Idiom Alignment evidence;
- validates the Kernel Ingress Proof Bundle;
- verifies that the Proof Bundle contains the exact digests evaluated by the
  same gate invocation;
- binds into the global Source-To-Intent Research Evidence Gate and Proof
  Bundle.

The contract is:

```text
source_to_intent_research_kernel_ingress_evidence_gate.ci.v0
```

## Security

The gate is metadata-only and source-free. It must not retain raw source,
extracted kernel source, Source Intent payloads, tensor values, runtime tensors,
compiler artifacts, backend binaries, generated code, device identifiers, host
paths, command lines, environment variables, benchmark output, or exception
text.

It must not import Triton modules, execute decorators, invoke JIT compilation,
discover plugins, access files by source path, or lower source text directly to
compiler artifacts.

## Consequences

Future Kernel Ingress syntax changes must update the focused Kernel Ingress
Evidence Gate and the global Source-To-Intent Research Evidence Gate together.

This still does not prove general Triton source ingestion, production parsing,
or native performance. Those claims remain blocked.
