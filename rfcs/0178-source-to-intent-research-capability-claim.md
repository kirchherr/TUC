# RFC 0178: Source-To-Intent Research Capability Claim

- Status: Accepted
- Date: 2026-06-17
- Owners: TUC maintainers
- Related artifacts:
  - `examples/source_to_intent_research_capability_claim.py`
  - `examples/source_to_intent_research_proof_bundle.py`
  - `examples/source_to_intent_research_evidence_gate.py`
  - `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`
  - `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`
  - `examples/source_to_intent_research_kernel_ingress_backend_equivalence.py`
  - `examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`
  - `examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`
  - `schemas/source_to_intent_research_capability_claim_report.v0.schema.json`
  - `docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM.md`
  - `tests/test_source_to_intent_research_capability_claim.py`

## Context

TUC now has a practical Kernel Ingress research slice that carries the current
MVP operation families through one accepted module-shaped `mvp_pipeline` kernel
and binds it to runtime matrix, coverage policy, backend alignment, proof
bundle, evidence gate, backend-equivalence, and backend-equivalence
shape-profile artifacts.

That is useful, but reviewers still need one explicit answer to the strategic
question: what does this prove, and what does it not prove?

## Decision

Add Source-To-Intent Research Capability Claim v0.

The report:

- emits a digest-only JSON claim artifact;
- validates the global proof bundle and global evidence gate;
- validates the focused Kernel Ingress proof bundle and evidence gate;
- validates runtime matrix, runtime backend equivalence, runtime backend
  equivalence shape profiles, runtime coverage policy, and runtime backend
  alignment;
- records the supported claim
  `bounded_universal_compute_research_slice`;
- records the scope
  `accepted_source_to_intent_kernel_ingress_mvp_pipeline`;
- records the combined operation path
  `matmul -> softmax -> reduction -> elementwise`;
- records trusted runtime backends `linear-sim` and `vector-sim`;
- records `reference-cpu` as the neutral baseline runtime backend for current
  portability comparison;
- records eight bounded backend-equivalence shape-profile cases across `base`
  and `alternate` declared tensor shape profiles;
- keeps production parser, general Triton ingestion, native performance,
  hardware certification, arbitrary backend execution, and vendor compiler
  replacement claims blocked.

## Security

The report is source-free and digest-only. It consumes existing structured
reports and text gates as evidence. It does not parse source text, import
Triton modules, execute source, run backends, access devices, discover plugins,
or emit benchmark data.

The report rejects forbidden source fragments and refuses drift in evidence
ordering, digest format, claim scope, blocked claims, and runtime coverage
counts.

## Consequences

TUC now has a single high-level artifact that states the current research claim
without inflating it into a production compiler or performance claim.

Future claim expansion must add lower-level evidence first, then update this
report, its schema, golden, tests, docs, and CI binding.
