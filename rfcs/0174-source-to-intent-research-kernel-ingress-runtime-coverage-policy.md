# RFC 0174: Source-To-Intent Research Kernel Ingress Runtime Coverage Policy

- Status: Accepted
- Date: 2026-06-17
- Owners: TUC maintainers
- Related artifacts:
  - `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`
  - `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
  - `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
  - `schemas/source_to_intent_research_kernel_ingress_runtime_coverage_policy_report.v0.schema.json`
  - `tests/test_source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY.md`
  - `rfcs/0173-source-to-intent-research-kernel-ingress-runtime-matrix.md`

## Context

The Runtime Matrix makes accepted Kernel Ingress runtime coverage visible. It
records backend sequences, terminal outputs, trace-step counts, and runtime
evidence digests.

TUC also needs a policy artifact that states which runtime coverage must remain
present before the research slice can continue to count as accepted evidence.
Without that policy, future changes could accidentally keep a matrix while
weakening the required cases or runtime digest obligations.

## Decision

Add Source-To-Intent Research Kernel Ingress Runtime Coverage Policy v0.

The policy:

- validates the Runtime Matrix contract;
- requires the current two accepted Kernel Ingress runtime cases;
- requires the current operation-family coverage;
- requires the current backend sequences and terminal outputs;
- requires one trace-step count policy for the current runtime model;
- requires runtime plan, execution trace, and reference correctness digest
  fields for each accepted case;
- remains metadata-only and source-free;
- is required by the Kernel Ingress Proof Bundle;
- is required by the focused Kernel Ingress Evidence Gate.

## Contract

```text
source_to_intent_research_kernel_ingress_runtime_coverage_policy.review.v0
```

Schema:

```text
schemas/source_to_intent_research_kernel_ingress_runtime_coverage_policy_report.v0.schema.json
```

## Security

The policy does not parse source text, execute source, evaluate decorators,
import Triton, expose Source Intent payloads, expose tensor values, emit backend
code, run subprocesses, access files, access devices, or load plugins.

The artifact forbids known source and value fragments in its rendered output.
It is a derived metadata artifact over already accepted Runtime Matrix evidence.

## Consequences

Future Kernel Ingress syntax or runtime behavior must update the Runtime Matrix,
the Runtime Coverage Policy, the Kernel Ingress Proof Bundle, the focused
Kernel Ingress Evidence Gate, the global Evidence Gate, and the global Proof
Bundle before it can count as accepted research scope.
