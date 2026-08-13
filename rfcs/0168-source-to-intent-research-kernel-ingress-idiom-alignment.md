# RFC 0168: Source-To-Intent Research Kernel Ingress Idiom Alignment

- Status: Accepted
- Date: 2026-06-16
- Area: Frontend, Source-To-Intent, Triton Compatibility Evidence
- Related:
  - `examples/source_to_intent_research_kernel_ingress_idiom_alignment.py`
  - `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
  - `examples/source_to_intent_research_evidence_gate.py`
  - `examples/source_to_intent_research_proof_bundle.py`
  - `schemas/source_to_intent_research_kernel_ingress_idiom_alignment_report.v0.schema.json`
  - `tests/test_source_to_intent_research_kernel_ingress_idiom_alignment.py`
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT.md`
  - `rfcs/0165-source-to-intent-research-kernel-ingress.md`
  - `rfcs/0167-source-to-intent-research-kernel-ingress-conformance-gate.md`

## Context

RFC 0165 added realistic Triton-module-shaped Kernel Ingress while keeping the
default source parser blocked. RFC 0167 then proved that accepted Kernel
Ingress outputs pass the reusable Source Intent Frontend Conformance path.

The remaining drift risk is operation-scope inflation: a module-shaped input
path can look more realistic while quietly expanding beyond the previously
covered MVP idioms.

## Decision

Add Source-To-Intent Research Kernel Ingress Idiom Alignment v0.

The new evidence artifact:

- consumes accepted Kernel Ingress results only;
- consumes the existing Triton Idiom Coverage report;
- consumes the Kernel Ingress Conformance Gate output;
- records the matched operation families and idiom identifiers;
- fails closed if accepted Kernel Ingress families are outside the covered MVP
  idiom scope;
- binds into `examples/source_to_intent_research_evidence_gate.py`;
- binds into `examples/source_to_intent_research_proof_bundle.py`.

The contract is:

```text
source_to_intent_research_kernel_ingress_idiom_alignment.scope.v0
```

## Security

The artifact is metadata-only. It does not retain raw module source, extracted
kernel source, Source Intent payloads, tensor values, runtime tensors, compiler
artifacts, backend binaries, generated code, device identifiers, host paths,
command lines, environment variables, benchmark output, or exception text.

It must not import Triton modules, execute decorators, invoke JIT compilation,
discover plugins, access files by source path, or lower source text directly to
compiler artifacts.

## Consequences

The research proof becomes slightly stricter: Kernel Ingress now has to prove
that accepted module-shaped inputs remain within covered MVP idioms before the
Evidence Gate and Proof Bundle can pass.

This still does not prove general Triton source ingestion, production parsing,
or native performance. Those claims remain blocked.
