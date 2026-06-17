# RFC 0176: Source-To-Intent Research Kernel Ingress Fixture Expansion

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
  - `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
  - `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
  - `schemas/source_to_intent_research_kernel_ingress_e2e_report.v0.schema.json`
  - `tests/test_source_to_intent_research_kernel_ingress.py`
  - `docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md`

## Context

Kernel Ingress v0 proved two realistic module-shaped cases:
`matmul_elementwise` and `softmax_reduction`.

That was enough for the first safe source-to-runtime slice, but too thin for
longer-term research evidence. TUC needs accepted fixtures that combine covered
idioms in new ways without widening into a general Triton parser.

## Decision

Add `matmul_reduction` as a third accepted Kernel Ingress fixture.

The new fixture:

- accepts only the existing bounded module shape;
- uses `tl.dot`, `tl.sum(axis=1)`, and `tl.store`;
- lowers through Source Intent plain data, metadata conversion, HAC-IR,
  runtime planning, trusted execution, and reference correctness;
- binds to terminal output `column_sum`;
- records the real planned backend sequence `linear-sim->vector-sim`;
- updates diagnostics, conformance, idiom alignment, runtime matrix, runtime
  coverage policy, runtime backend alignment, proof bundle, evidence gate, and
  schemas together.

## Security

This RFC does not approve general Triton source ingestion, production parsing,
native performance claims, backend plugin execution, device access, or source
execution.

The fixture is static test data. Reports remain source-free and value-free,
recording only metadata, digests, operation families, backend sequences,
terminal output names, trace counts, and pass/fail status.

## Consequences

Kernel Ingress now has three accepted module-shaped research cases while the
default source parser remains blocked.

The expansion improves the practical evidence base without changing the trust
boundary: future syntax growth still requires explicit diagnostics, budgets,
conformance, runtime evidence, and evidence-gate updates.
