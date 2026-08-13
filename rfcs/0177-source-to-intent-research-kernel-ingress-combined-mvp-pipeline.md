# RFC 0177: Source-To-Intent Research Kernel Ingress Combined MVP Pipeline

- Status: Accepted
- Date: 2026-06-17
- Owners: TUC maintainers
- Related artifacts:
  - `examples/source_to_intent_research_kernel_ingress.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`
  - `examples/source_to_intent_research_kernel_ingress_conformance_gate.py`
  - `examples/source_to_intent_research_kernel_ingress_diagnostics.py`
  - `examples/source_to_intent_research_kernel_ingress_idiom_alignment.py`
  - `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
  - `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
  - `schemas/source_to_intent_research_kernel_ingress_e2e_report.v0.schema.json`
  - `tests/test_source_to_intent_research_kernel_ingress.py`
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md`

## Context

Kernel Ingress had accepted realistic module-shaped fixtures for paired MVP
operation families. That proved source-shaped ingress could reach runtime
evidence, but it did not yet show one accepted module-shaped kernel carrying
all current MVP families through the same path.

TUC needs a stronger practical research slice without turning the explicit
research parser into a general Triton parser.

## Decision

Add `mvp_pipeline` as a fourth accepted Kernel Ingress fixture.

The new fixture:

- accepts only the existing bounded module shape;
- uses `tl.dot`, `tl.softmax(axis=1)`, `tl.sum(axis=1)`, `tl.where`, and
  `tl.store`;
- covers `matmul -> softmax -> reduction -> elementwise` in one kernel;
- lowers through Source Intent plain data, metadata conversion, HAC-IR,
  runtime planning, trusted execution, and reference correctness;
- binds to terminal output `stable`;
- records the real planned backend sequence
  `linear-sim->vector-sim->vector-sim->vector-sim`;
- records a four-step runtime trace count;
- updates diagnostics, conformance, idiom alignment, runtime matrix, runtime
  coverage policy, runtime backend alignment, proof bundle, evidence gate, and
  schemas together.

## Security

This RFC does not approve general Triton source ingestion, production parsing,
native performance claims, backend plugin execution, device access, or source
execution.

The fixture remains static test data. Reports stay source-free and value-free,
recording only metadata, digests, operation families, backend sequences,
terminal output names, trace counts, and pass/fail status.

## Consequences

Kernel Ingress now has four accepted module-shaped research cases. The fourth
case proves all current MVP operation families can flow through one realistic
module-shaped source buffer while the default source parser remains blocked.

Future syntax growth still requires explicit diagnostics, budgets,
conformance, runtime evidence, and evidence-gate updates before it can count
as accepted research scope.
