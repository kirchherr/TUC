# RFC 0175: Source-To-Intent Research Kernel Ingress Runtime Backend Alignment

- Status: Accepted
- Date: 2026-06-17
- Owners: TUC maintainers
- Related artifacts:
  - `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`
  - `examples/runtime_executor_conformance.py`
  - `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
  - `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
  - `examples/source_to_intent_research_evidence_gate.py`
  - `examples/source_to_intent_research_proof_bundle.py`
  - `schemas/source_to_intent_research_kernel_ingress_runtime_backend_alignment_report.v0.schema.json`
  - `tests/test_source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT.md`
  - `rfcs/0173-source-to-intent-research-kernel-ingress-runtime-matrix.md`
  - `rfcs/0174-source-to-intent-research-kernel-ingress-runtime-coverage-policy.md`

## Context

The Kernel Ingress Runtime Matrix records accepted backend sequences, and the
Runtime Coverage Policy states which runtime cases must remain covered.

That still leaves one practical audit question: are the backend names in those
accepted sequences backed by the trusted Runtime Executor conformance registry,
or are they merely strings in a matrix?

TUC should answer that question before the proof slice grows. The research
claim is not that arbitrary hardware is supported. The claim is that accepted
source-shaped cases flow into explicit, capability-checked runtime planning and
trusted prototype execution evidence.

## Decision

Add Source-To-Intent Research Kernel Ingress Runtime Backend Alignment v0.

The alignment report:

- validates the Runtime Matrix contract;
- validates the Runtime Coverage Policy contract;
- validates the Runtime Executor Conformance contract;
- requires the current accepted backend names `linear-sim` and `vector-sim`;
- derives trusted supported operation families from conformance checked cases;
- verifies every accepted Kernel Ingress case has its operation families
  covered by its planned backend sequence;
- records runtime matrix, coverage policy, and runtime conformance digests;
- remains metadata-only and source-free;
- is required by the Kernel Ingress Proof Bundle;
- is required by the focused Kernel Ingress Evidence Gate.

## Contract

```text
source_to_intent_research_kernel_ingress_runtime_backend_alignment.trusted_executor.v0
```

Schema:

```text
schemas/source_to_intent_research_kernel_ingress_runtime_backend_alignment_report.v0.schema.json
```

## Security

The alignment report does not parse source text, execute source, evaluate
decorators, import Triton, expose Source Intent payloads, expose tensor values,
emit backend code, run subprocesses, access files, access devices, dynamically
import backend code, or load plugins.

The report forbids known source and value fragments in its rendered output. It
is a derived metadata artifact over already accepted Runtime Matrix, Runtime
Coverage Policy, and Runtime Executor Conformance evidence.

## Consequences

Future Kernel Ingress syntax or runtime behavior must update the Runtime
Matrix, Runtime Coverage Policy, Runtime Backend Alignment, Kernel Ingress
Proof Bundle, focused Kernel Ingress Evidence Gate, global Evidence Gate, and
global Proof Bundle before it can count as accepted research scope.

This still does not prove general Triton source ingestion, production parsing,
native performance, or arbitrary backend execution. Those claims remain
blocked.
