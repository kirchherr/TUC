# Roadmap Status

This file tracks concrete progress against the roadmap. It is deliberately
shorter and more operational than `ROADMAP.md`.

## Strategic Priority

TUC is now led by [TUC Master Plan](../TUC_MASTER_PLAN.md). The project identity
is **The Universal Compute**: a proof that compute intent can flow through a
hardware-independent interface into capability-driven runtime planning.

## Completed

### Phase 0: Project Foundation

- Open-source repository structure.
- Docker development environment.
- Governance, contribution, security, issue, PR, and RFC scaffolding.
- Initial Python package under `src/tuc`.
- Prototype backend capability model.
- Linear algebra simulator backend.
- Rule-based runtime partitioning.
- Unit tests and Phase 0 vertical-slice example.
- Initial commit pushed to GitHub.
- Strategic master plan promoted as the top-level project guide.
- [External Review Triage 2026-06-22](EXTERNAL_REVIEW_TRIAGE_2026_06_22.md)
  records which external review suggestions are adopted now, adopted later, or
  rejected to avoid diluting the research claim.
- [Research Onboarding Slice](RESEARCH_ONBOARDING_SLICE.md) provides a short
  first-run path from the Universal Compute claim to Objective Alpha executable
  evidence.
- [Research Onboarding Evidence](RESEARCH_ONBOARDING_EVIDENCE.md) emits the
  first-run proof path as schema-versioned review evidence with blocked claims
  and blocked execution surfaces.
- [Minimal TUC Walkthrough](MINIMAL_TUC_WALKTHROUGH.md) gives reviewers the
  shortest current path through compute intent, trusted runtime execution,
  runtime evidence, replay verification, backend equivalence, and evidence
  gates without expanding the README.
- [Proof Of Backend Equivalence](PROOF_OF_BACKEND_EQUIVALENCE.md) promotes
  backend equivalence to an explicit proof type with required evidence, current
  artifacts, non-claims, and a secure review checklist.
- Proof Of Backend Equivalence now has a canonical entrypoint at
  `examples/proof_of_backend_equivalence.py`, schema at
  `schemas/proof_of_backend_equivalence_report.v0.schema.json`, and
  deterministic golden evidence at
  `tests/golden/proofs/proof_of_backend_equivalence.json`, binding the mixed
  `reference-cpu` versus `systolic-sim + vector-sim` equivalence report by
  digest without serializing tensor values or claiming native execution.
- [Runtime Transfer Evidence](RUNTIME_TRANSFER_EVIDENCE.md) records the current
  planned `device_sram -> host_ram` transfer from the systolic simulator proof
  as data-only evidence, with schema at
  `schemas/runtime_transfer_evidence_report.v0.schema.json`, example
  `examples/runtime_transfer_evidence.py`, and deterministic golden evidence at
  `tests/golden/runtime_transfer_evidence/current_report.json`. Transfer cost
  fields are deterministic planning estimates, not hardware measurements or
  native performance evidence.
- [Runtime Transfer Trace Index](RUNTIME_TRANSFER_TRACE_INDEX.md) binds that
  planned backend-equivalence transfer to concrete producer and consumer
  Runtime Execution Trace steps, with schema at
  `schemas/runtime_transfer_trace_index_report.v0.schema.json`, example
  `examples/runtime_transfer_trace_index.py`, and deterministic golden evidence
  at `tests/golden/runtime_transfer_trace_index/current_report.json`. The
  index is required by Runtime Evidence Matrix and Runtime Evidence Gate for
  the systolic backend-equivalence proof slice while preserving the
  `transfer_not_materialized_as_runtime_step` boundary and keeping residency,
  handles, raw values, and native performance claims blocked.
- [RFC 0212: Runtime Layout Conversion Evidence](../rfcs/0212-runtime-layout-conversion-evidence.md)
  defines the next optional data-only proof boundary for explicit planned layout
  transitions before any native converter, allocation handle, or real residency
  claim is accepted.
- Runtime Layout Conversion Evidence v0 records the current planned
  `blocked -> row_major` transition from the mixed backend-equivalence plan as
  data-only evidence at
  `schemas/runtime_layout_conversion_evidence_report.v0.schema.json`, with
  deterministic golden evidence at
  `tests/golden/runtime_layout_conversion_evidence/current_report.json`.
- Runtime Evidence Matrix now requires Runtime Layout Conversion Evidence as
  `runtime_layout_conversion_evidence_mixed` gate evidence for the mixed
  backend-equivalence graph.
- [Runtime Layout Conversion Gate Readiness](RUNTIME_LAYOUT_CONVERSION_GATE_READINESS.md)
  records the exact promotion prerequisites for making layout-conversion
  evidence gate-required, with schema at
  `schemas/runtime_layout_conversion_gate_readiness_report.v0.schema.json` and
  deterministic blocked golden evidence at
  `tests/golden/runtime_layout_conversion_gate_readiness/current_report.json`.
- Runtime Layout Conversion Evidence now has a second independent
  `runtime_layout_conversion_reduction_slice` proof fixture with deterministic
  golden evidence at
  `tests/golden/runtime_layout_conversion_evidence/second_slice_report.json`,
  clearing the Readiness blocker for `second_independent_layout_conversion_slice`.
- Runtime Layout Conversion Gate Readiness now verifies the exact Matrix graph,
  artifact kind, and `runtime_layout_conversion_evidence_mixed` artifact ID for
  the target evidence, clearing the `gate_exact_artifact_binding` blocker
  before gate enforcement was activated.
- [Runtime Layout Conversion Digest Binding](RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING.md)
  now binds Runtime Layout Conversion Evidence to Runtime HS-IR Plan Alignment
  and Runtime Tensor Store Evidence with schema at
  `schemas/runtime_layout_conversion_digest_binding_report.v0.schema.json` and
  deterministic golden evidence at
  `tests/golden/runtime_layout_conversion_digest_binding/current_report.json`,
  clearing the `hs_ir_and_tensor_store_digest_binding` readiness blocker.
- Runtime Layout Conversion Gate Readiness is now `ready` with all seven checks
  passed, and `runtime_layout_conversion_evidence` is now Runtime Evidence
  Gate-required for the mixed backend-equivalence graph.
- [Runtime Layout Conversion Gate Promotion Policy](RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY.md)
  records the graph-scoped promotion candidate with schema at
  `schemas/runtime_layout_conversion_gate_promotion_policy_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/runtime_layout_conversion_gate_promotion_policy/current_report.json`,
  `promotion_ready: true`, and
  `enforcement_status: enforced_by_runtime_evidence_gate`.
- Runtime Evidence Gate now enforces Layout Conversion Evidence for
  `runtime_mixed_backend_equivalence`, binding the report to Mixed Backend
  Equivalence, Mixed Planning Explanation, HS-IR Plan Alignment,
  Mixed Tensor Store Evidence, Digest Binding, and Promotion Policy metadata.
- [Runtime Transfer Trace Replay Verifier](RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER.md)
  replay-checks serialized Transfer Evidence and Trace Index reports by metadata
  digest, with schema at
  `schemas/runtime_transfer_trace_replay_verifier_report.v0.schema.json`, example
  `examples/runtime_transfer_trace_replay_verifier.py`, and deterministic
  golden evidence at
  `tests/golden/runtime_transfer_trace_replay_verifier/current_report.json`.
- [Runtime Backend Equivalence Transfer Binding](RUNTIME_BACKEND_EQUIVALENCE_TRANSFER_BINDING.md)
  binds systolic Runtime Backend Equivalence to verified transfer trace replay
  by metadata digest, with schema at
  `schemas/runtime_backend_equivalence_transfer_binding_report.v0.schema.json`, example
  `examples/runtime_backend_equivalence_transfer_binding.py`, and deterministic
  golden evidence at
  `tests/golden/runtime_backend_equivalence_transfer_binding/current_report.json`.
- Runtime Evidence Matrix and Runtime Evidence Gate now require both
  `runtime_transfer_trace_replay_verifier_systolic` and
  `runtime_backend_equivalence_transfer_binding_systolic` for
  `runtime_backend_equivalence`, closing the graph-scoped chain from systolic
  terminal-output equivalence to transfer-boundary replay evidence.
- [Runtime Layout Conversion Trace Index](RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX.md)
  now binds the mixed slice's planned `blocked -> row_major` conversion to
  producer and consumer Runtime Execution Trace step indexes, with schema at
  `schemas/runtime_layout_conversion_trace_index_report.v0.schema.json`, example
  `examples/runtime_layout_conversion_trace_index.py`, and deterministic golden
  evidence at
  `tests/golden/runtime_layout_conversion_trace_index/current_report.json`.
- Runtime Evidence Matrix and Runtime Evidence Gate now require
  `runtime_layout_conversion_trace_index_mixed` for
  `runtime_mixed_backend_equivalence`, binding the trace index to the same graph,
  partition-plan digest, layout-conversion evidence digest, conversion count,
  mixed candidate trace-step count, and exact Matrix artifact ID.
- Runtime Layout Conversion Trace Replay Verifier v0 replay-checks serialized
  Layout Conversion Evidence and Trace Index reports by metadata digest, with
  schema at
  `schemas/runtime_layout_conversion_trace_replay_verifier_report.v0.schema.json`,
  example `examples/runtime_layout_conversion_trace_replay_verifier.py`, and
  deterministic golden evidence at
  `tests/golden/runtime_layout_conversion_trace_replay_verifier/current_report.json`.
- [Runtime Backend Equivalence Layout Binding](RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING.md)
  binds mixed Runtime Backend Equivalence to verified layout trace replay by
  metadata digest, with schema at
  `schemas/runtime_backend_equivalence_layout_binding_report.v0.schema.json`,
  example `examples/runtime_backend_equivalence_layout_binding.py`, and
  deterministic golden evidence at
  `tests/golden/runtime_backend_equivalence_layout_binding/current_report.json`.
- Runtime Evidence Matrix and Runtime Evidence Gate now require both
  `runtime_layout_conversion_trace_replay_verifier_mixed` and
  `runtime_backend_equivalence_layout_binding_mixed` for
  `runtime_mixed_backend_equivalence`, closing the graph-scoped chain from
  mixed terminal-output equivalence to layout-transition replay evidence.
- [Objective Alpha Public Proof Bundle](OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE.md)
  binds proof execution, runtime evidence matrix, runtime evidence gate, Proof
  Of Backend Equivalence, Runtime Execution Output Closure, transfer-boundary
  trace index, replay, and binding, layout-transition trace index, replay, and
  binding, allocation reconciliation, Runtime Memory Planning Gate, onboarding
  evidence, Source-To-Intent Research Proof Bundle, and Kernel Ingress Evidence
  Gate as one digest-only review artifact, with explicit `entry_count` and
  `entry_capacity` metadata showing the current 16-entry public proof surface is
  full and requires a deliberate capacity decision for future additions.
- [Objective Alpha Public Proof Bundle Gate](OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md) emits `examples/objective_alpha_public_proof_bundle_gate.py` with schema `schemas/objective_alpha_public_proof_bundle_gate_report.v0.schema.json`, proving the public bundle keeps fixed evidence IDs, fixed entry points, fixed artifact kinds, direct transfer/layout trace-index public entries, direct Source-To-Intent/Kernel Ingress public entries, fixed public entry capacity, digest-only policy, and blocked non-claims; canonical doc path: `docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md`.
- [Objective Alpha Evidence Extension Policy](OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY.md) emits `examples/objective_alpha_evidence_extension_policy.py` with schema `schemas/objective_alpha_evidence_extension_policy_report.v0.schema.json` and golden `tests/golden/proofs/objective_alpha_evidence_extension_policy.json`, proving the current 16-entry public bundle remains the stable first review entrypoint and future public evidence growth requires a deliberate RFC, separate public evidence catalog, or successor objective; canonical doc path: `docs/OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY.md`.
- [Objective Alpha Public Evidence Catalog](OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md) emits `examples/objective_alpha_public_evidence_catalog.py` with schema `schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json` and golden `tests/golden/proofs/objective_alpha_public_evidence_catalog.json`, binding the Extension Policy as the initial digest-only governance entry and Runtime Backend Equivalence Portfolio as the first digest-only `runtime_proof` entry while keeping the growth surface RFC-bound outside the fixed 16-entry Public Proof Bundle; canonical doc path: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md`.
- [Objective Alpha Public Evidence Catalog Admission Gate](OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md) emits `examples/objective_alpha_public_evidence_catalog_admission_gate.py` with schema `schemas/objective_alpha_public_evidence_catalog_admission_gate_report.v0.schema.json` and golden `tests/golden/proofs/objective_alpha_public_evidence_catalog_admission_gate.json`, machine-checking the catalog's append-only, RFC-bound, digest-only, source-free admission rules, binding the first runtime-proof catalog entry, and preserving blocked claims and execution surfaces; canonical doc path: `docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md`.
- Objective Alpha Public Evidence Catalog Entry Admission Pattern now derives the catalog's expected evidence IDs, entry points, artifact kinds, extension tiers, digest source labels, and raw-output policies from typed data-only specs governed by `rfcs/0236-objective-alpha-catalog-entry-admission-pattern.md`, reducing review drift for future catalog additions without adding execution, plugin, path-resolution, device, source-ingress, or native-performance surfaces.
- Objective Alpha Public Evidence Catalog now includes `source_to_intent_research_kernel_ingress_proof_bundle` as the first `frontend_runtime_proof` catalog entry, binding the Source-To-Intent Kernel Ingress Proof Bundle by SHA-256 metadata digest while keeping the fixed Public Proof Bundle unchanged and preserving source-free, digest-only public evidence.
- Objective Alpha Public Evidence Catalog now includes `source_to_intent_research_capability_claim_gate` as the first `claim_boundary` catalog entry, binding the CI-facing Capability Claim Gate by SHA-256 metadata digest while keeping the fixed Public Proof Bundle unchanged and preserving source-free, digest-only public evidence.
- Objective Alpha Public Evidence Catalog Extension-Tier Coverage now emits `catalog_required_extension_tiers`, `catalog_missing_extension_tiers`, and `catalog_extension_tier_coverage_status`, and the admission gate requires complete coverage for `governance`, `runtime_proof`, `frontend_runtime_proof`, and `claim_boundary` with no new source, execution, path-resolution, device, plugin, or native-performance surface.
- [Triton Integration Readiness](TRITON_INTEGRATION_READINESS.md) now turns the next Real Triton Integration milestone into data-only review evidence at `examples/triton_integration_readiness.py`, with schema at `schemas/triton_integration_readiness_report.v0.schema.json`, deterministic golden evidence at `tests/golden/frontend/triton_integration_readiness_report.json`, current `integration_status: not_ready`, and direct Triton source ingestion plus `@triton.jit` execution still blocked.
- [Source-To-Intent Next Syntax Slice](SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE.md) now satisfies the broader parser RFC, semantic mapping corpus, Source Intent golden, and semantic mapping fuzz/property prerequisites for Triton Integration Readiness through `examples/source_to_intent_next_syntax_slice.py`, schema `schemas/source_to_intent_next_syntax_report.v0.schema.json`, report golden `tests/golden/frontend/source_to_intent_next_syntax_report.json`, and Source Intent golden `tests/golden/frontend/source_to_intent_next_syntax_source_intent.json`, while direct source ingestion and `@triton.jit` execution remain blocked.
- [External Frontend Package Conformance](EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE.md) now satisfies the final Triton Integration Readiness prerequisite through `examples/external_frontend_package_conformance.py`, schema `schemas/external_frontend_package_conformance_report.v0.schema.json`, and golden `tests/golden/frontend/external_frontend_package_conformance_report.json`, proving package manifests and digest-only Source Intent fixtures can be reviewed without package import, plugin discovery, source ingestion, or JIT execution.
- [Real Triton Integration Admission Gate](REAL_TRITON_INTEGRATION_ADMISSION_GATE.md) now binds Triton Integration Readiness, External Frontend Package Conformance, and [Real Triton Integration Threat Model](REAL_TRITON_INTEGRATION_THREAT_MODEL.md) evidence by digest through `examples/real_triton_integration_admission_gate.py`, schema `schemas/real_triton_integration_admission_gate_report.v0.schema.json`, and golden `tests/golden/frontend/real_triton_integration_admission_gate_report.json`, canonical doc paths `docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md` and `docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md`, while `admitted: false` keeps source ingestion, package import, plugin discovery, JIT, device access, generated artifact execution, and native backend execution blocked until dedicated surface gates exist.
- [Source Ingestion Quarantine Gate](SOURCE_INGESTION_QUARANTINE_GATE.md) is now the first dedicated Real Triton Integration surface gate through `examples/source_ingestion_quarantine_gate.py`, schema `schemas/source_ingestion_quarantine_gate_report.v0.schema.json`, golden `tests/golden/frontend/source_ingestion_quarantine_gate_report.json`, and canonical doc path `docs/SOURCE_INGESTION_QUARANTINE_GATE.md`, binding admission, parser-gate, preflight, and threat-model evidence by digest while source-to-ComputeGraph, source-to-HAC-IR, source-to-runtime-plan, import, function-object inspection, JIT, raw source serialization, and generated artifact execution remain blocked.
- Proof-of-abstraction example for Objective Alpha.
- Golden proof-of-abstraction output for reproducible Level 3 validation.
- Golden runtime-plan dump for proof-of-abstraction placement and transfer
  reasoning.
- Proof-of-reduction example for Objective Alpha's second graph family.
- Golden proof, HAC-IR, and runtime-plan dumps for proof-of-reduction
  validation.
- Proof-report metadata for proof version, graph family, and backend set.
- Proof artifact review checklist for proof examples, metadata, goldens, and
  proof documentation.
- Performance proof boundary for leaky abstraction and planner-overhead limits
  of the current correctness proof.
- Diagnostic performance-proof RFC report for future native performance claim
  proposals without benchmark execution or execution permission.
- Diagnostic performance claim threshold policy report for accepted,
  digest-pinned threshold metadata before "near native" claims can be reviewed.
- Diagnostic performance acceptance criteria report for accepted, digest-pinned
  pass/fail metadata before benchmark artifacts can count as passing evidence.
- Diagnostic Triton idiom coverage report for execution-free metadata examples
  and golden evidence, with direct source ingestion still blocked.
- Runtime Executor v0 for trusted in-process prototype backend execution of
  already-compiled graphs.
- Proof-of-execution example with deterministic proof and execution-trace
  goldens.
- Runtime Executor MVP-family execution trace for the Triton-like metadata graph.
- Trusted Runtime Backend Executor Contract v0 with deterministic golden
  evidence for the fixed in-process prototype executor registry.
- Runtime execution readiness report that gates proof execution against trusted
  backend executor contracts before kernels run.
- Triton metadata MVP-family runtime readiness golden before execution.
- Runtime Evidence Matrix v0 with schema-versioned proof inventory and
  deterministic golden at `tests/golden/proofs/runtime_evidence_matrix_report.json`.
- Runtime Evidence Matrix v0 is complete across current graph fixtures.
- Runtime Evidence Matrix now records graph-scoped required evidence kinds and
  inventories the systolic, vector, and mixed backend-equivalence fixtures under
  the scoped `backend_equivalence` requirement.
- Runtime Evidence Gate now binds each backend-equivalence report to its Runtime
  Evidence Matrix graph entry, verifying scoped `backend_equivalence` inventory
  coverage before the report can count as passing gate evidence.
- Runtime Backend Equivalence Portfolio v0 aggregates the systolic, vector, and
  mixed accelerator equivalence slices into one schema-versioned
  backend-diversity artifact at
  `schemas/runtime_backend_equivalence_portfolio_report.v0.schema.json`, with
  deterministic golden evidence at
  `tests/golden/runtime_backend_equivalence/portfolio_report.json`.
- Runtime Evidence Gate now binds the Backend Equivalence Portfolio back to the
  exact three equivalence reports checked during the same gate invocation,
  verifying slice IDs, run IDs, backend sequences, comparison metadata digests,
  backend families, pass status, and raw-value omission policy.
- Runtime Evidence Matrix now inventories the Backend Equivalence Portfolio as
  its own scoped graph with `backend_equivalence_portfolio` and
  `backend_equivalence_portfolio_policy` requirements, and Runtime Evidence
  Gate verifies that Matrix coverage before portfolio evidence can count as
  passing merge evidence.
- Runtime Backend Equivalence Portfolio Policy v0 declares the accepted
  backend-diversity slice membership, backend sequences, minimum comparison
  counts, and backend-family coverage at
  `schemas/runtime_backend_equivalence_portfolio_policy_report.v0.schema.json`,
  with deterministic golden evidence at
  `tests/golden/runtime_backend_equivalence/portfolio_policy_report.json`.
- Runtime Evidence Gate now binds the Backend Equivalence Portfolio Policy to
  the checked portfolio before portfolio evidence can count as passing merge
  evidence.
- Runtime Evidence Gate now binds backend-equivalence and portfolio Matrix
  coverage to exact artifact IDs, preventing kind-only Matrix coverage from
  accepting the wrong concrete evidence artifact.
- Runtime Evidence Gate Matrix Coverage v0 emits the exact gate-required
  backend-equivalence and portfolio Matrix bindings as schema-versioned JSON
  at `schemas/runtime_evidence_gate_matrix_coverage_report.v0.schema.json`,
  with deterministic golden evidence at
  `tests/golden/proofs/runtime_evidence_gate_matrix_coverage_report.json`, and
  Runtime Evidence Gate requires that audit to pass.
- Runtime HS-IR Plan Alignment v0 binds HS-IR backend/layout decisions to the
  accepted `PartitionPlan` and observed `RuntimeExecutionTrace` for the mixed
  accelerator proof slice, with schema at
  `schemas/runtime_hs_ir_plan_alignment_report.v0.schema.json` and
  deterministic golden evidence at
  `tests/golden/runtime_hs_ir_plan_alignment/mixed_report.json`.
- Runtime Evidence Matrix now inventories Runtime HS-IR Plan Alignment as
  required scoped evidence for `runtime_mixed_backend_equivalence`, and Runtime
  Evidence Gate verifies the report, backend-sequence binding, and exact
  `runtime_hs_ir_plan_alignment_mixed` artifact ID before the mixed
  accelerator slice can count as passing gate evidence.
- Runtime Executor Conformance v0 with schema-versioned trusted registry
  conformance at `schemas/runtime_executor_conformance_report.v0.schema.json`
  and deterministic golden at
  `tests/golden/runtime_executor_conformance/trusted_runtime_executor_registry.json`,
  now including `vector-sim` support/rejection behavior.
- Runtime Evidence Gate v0 with deterministic golden at
  `tests/golden/proofs/runtime_evidence_gate.txt` and CI coverage in the
  `python` workflow job.
- Runtime Candidate Score Evidence v0 with schema at
  `schemas/runtime_candidate_score_evidence_report.v0.schema.json`,
  deterministic golden at
  `tests/golden/runtime_candidate_score_evidence/profiled_candidate_score_report.json`,
  and CI coverage in the `python` workflow job.
- Runtime Planning Explanation v0 with schema at
  `schemas/runtime_planning_explanation_report.v0.schema.json`,
  deterministic goldens at
  `tests/golden/runtime_planning_explanation/systolic_report.json` and
  `tests/golden/runtime_planning_explanation/mixed_backend_equivalence_report.json`,
  and data-only explanation of accepted systolic and mixed placement,
  fallback/no-fallback behavior, backend sequence, candidate-score visibility,
  and movement bytes.
- Runtime Evidence Matrix and Runtime Evidence Gate now require and bind
  Runtime Planning Explanation for `runtime_backend_equivalence` and
  `runtime_mixed_backend_equivalence`, including exact
  `runtime_planning_explanation_systolic` and
  `runtime_planning_explanation_mixed` Matrix artifact IDs and gate output
  lines for backend sequence, selection kinds, and movement bytes.
- Runtime Candidate Scoring Policy v0 with schema at
  `schemas/runtime_candidate_scoring_policy.v0.schema.json` and deterministic
  golden at
  `tests/golden/runtime_candidate_scoring_policy/current_policy_report.json`.
- Runtime Candidate Scoring Conformance v0 with schema at
  `schemas/runtime_candidate_scoring_conformance_report.v0.schema.json` and
  deterministic golden at
  `tests/golden/runtime_candidate_scoring_conformance/current_conformance_report.json`.
- Runtime Candidate Scoring Gate v0 with deterministic golden evidence at
  `tests/golden/runtime_candidate_scoring_gate/current_gate.txt` and CI coverage
  in the `python` workflow job.
- Runtime Buffer Lifetime v0 with schema at
  `schemas/runtime_buffer_lifetime_report.v0.schema.json` and deterministic
  golden at `tests/golden/runtime_buffer_lifetime/current_report.json`,
  exposing `lifetime_metadata_digest` for downstream allocation binding.
- Runtime Allocation Plan v0 with schema at
  `schemas/runtime_allocation_plan_report.v0.schema.json`, deterministic
  golden at `tests/golden/runtime_allocation_plan/current_report.json`, and a
  source lifetime metadata digest plus allocation metadata digest for
  downstream budget binding.
- Runtime Memory Budget v0 with schema at
  `schemas/runtime_memory_budget_report.v0.schema.json`, deterministic golden
  at `tests/golden/runtime_memory_budget/current_report.json`, and source
  allocation metadata digest binding.
- Runtime Allocation Request Manifest v0 with schema at
  `schemas/runtime_allocation_request_manifest_report.v0.schema.json`,
  deterministic golden at
  `tests/golden/runtime_allocation_request_manifest/current_report.json`, and
  no-runtime-handles future allocator admission requests bound to Allocation
  Plan and Memory Budget metadata.
- Runtime Allocation Admission v0 with schema at
  `schemas/runtime_allocation_admission_report.v0.schema.json`,
  deterministic golden at
  `tests/golden/runtime_allocation_admission/current_report.json`, and
  data-only allocator-admission decisions bound to Allocation Request Manifest
  and Memory Budget evidence before any allocator behavior exists.
- Runtime Allocation Receipt v0 with schema at
  `schemas/runtime_allocation_receipt_report.v0.schema.json`, deterministic
  golden at `tests/golden/runtime_allocation_receipt/current_report.json`, and
  dry-run allocation ledger entries bound to Allocation Admission evidence
  without pointers, handles, memory pools, or device access.
- Runtime Memory Planning Gate v0 with deterministic golden evidence at
  `tests/golden/runtime_memory_planning_gate/current_gate.txt` and CI coverage
  in the `python` workflow job, now verifying Allocation Plan binding to Buffer
  Lifetime, Memory Budget binding to Allocation Plan, Allocation Request
  Manifest binding to Allocation Plan and Memory Budget, Allocation Admission
  binding to Request Manifest and Memory Budget, and Allocation Receipt binding
  to Allocation Admission in the same gate invocation.
- Systolic simulator proof with `systolic-sim` placement, `device_sram`
  memory-domain evidence, `blocked -> row_major` layout-conversion evidence,
  deterministic proof/HAC-IR/runtime-plan/compiler-decision/readiness/trace/
  tensor-store-evidence goldens, and Runtime Evidence Matrix coverage.
- Systolic capability manifest path proving that `systolic-sim` can enter TUC
  as explicit JSON capability data for planning while execution remains gated
  by the trusted Runtime Executor registry.
- Manifest Claim Review report for accepted and intentionally blocked backend
  capability manifests, with schema at
  `schemas/manifest_claim_review_report.v0.schema.json` and deterministic
  golden evidence at
  `tests/golden/backend_claim_review/manifest_claim_review_report.json`.
- Backend author path now runs Manifest Claim Review before registry loading,
  compiler planning, conformance, or trusted lowering, with golden evidence at
  `tests/golden/backend_claim_review/external_vector_author_report.json`.
- Backend Author Readiness report that summarizes claim review, registry
  loading, compiler assignment, conformance, and assigned-subgraph lowering,
  with schema at `schemas/backend_author_readiness_report.v0.schema.json` and
  deterministic golden evidence at
  `tests/golden/backend_author_readiness/external_vector_readiness_report.json`.
- Backend Author Evidence Gate with deterministic golden evidence at
  `tests/golden/backend_author_readiness/backend_author_evidence_gate.txt` and
  CI coverage in the `python` workflow job.
- [Backend Plugin Lifecycle Policy](BACKEND_PLUGIN_LIFECYCLE_POLICY.md) records
  the current blocking policy for future executable backend plugins, with schema
  at `schemas/backend_plugin_lifecycle_policy_report.v0.schema.json`, golden
  evidence at `tests/golden/backend_plugin_lifecycle_policy/current_report.json`,
  and RFC [0217](../rfcs/0217-backend-plugin-lifecycle-policy.md). It keeps
  plugin discovery, artifact execution, and native plugin ABI loading disabled
  even though the data-only lifecycle evidence gate is complete.
- [Backend Plugin Sandbox Model](BACKEND_PLUGIN_SANDBOX_MODEL.md) now satisfies
  the Lifecycle Policy `sandbox_model` requirement with data-only evidence at
  `schemas/backend_plugin_sandbox_model_report.v0.schema.json`, deterministic
  golden evidence at `tests/golden/backend_plugin_sandbox_model/current_report.json`,
  and RFC [0218](../rfcs/0218-backend-plugin-sandbox-model.md), while keeping
  `execution_allowed: false` and `execution_permission: not_granted`.
- [Backend Plugin Artifact Provenance](BACKEND_PLUGIN_ARTIFACT_PROVENANCE.md)
  now satisfies the Lifecycle Policy `artifact_provenance` requirement with
  digest-bound data-only evidence at
  `schemas/backend_plugin_artifact_provenance_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/backend_plugin_artifact_provenance/current_report.json`, and
  RFC [0219](../rfcs/0219-backend-plugin-artifact-provenance.md), while
  keeping `execution_allowed: false` and `execution_permission: not_granted`.
- [Backend Plugin Resource Budget](BACKEND_PLUGIN_RESOURCE_BUDGET.md) now
  satisfies the Lifecycle Policy `resource_budget` requirement with static
  data-only budget evidence at
  `schemas/backend_plugin_resource_budget_report.v0.schema.json`, deterministic
  golden evidence at `tests/golden/backend_plugin_resource_budget/current_report.json`,
  and RFC [0220](../rfcs/0220-backend-plugin-resource-budget.md), while
  keeping `execution_allowed: false` and `execution_permission: not_granted`.
- [Backend Plugin Fuzz Negative Tests](BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS.md)
  now satisfies the Lifecycle Policy `fuzz_negative_tests` requirement with
  deterministic data-only rejection evidence at
  `schemas/backend_plugin_fuzz_negative_tests_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/backend_plugin_fuzz_negative_tests/current_report.json`, and
  RFC [0221](../rfcs/0221-backend-plugin-fuzz-negative-tests.md), while
  keeping `execution_allowed: false` and `execution_permission: not_granted`.
- [Backend Plugin Maintainer Approval](BACKEND_PLUGIN_MAINTAINER_APPROVAL.md)
  now satisfies the Lifecycle Policy `maintainer_approval` requirement with
  data-only approval evidence at
  `schemas/backend_plugin_maintainer_approval_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/backend_plugin_maintainer_approval/current_report.json`, and
  RFC [0222](../rfcs/0222-backend-plugin-maintainer-approval.md), while
  keeping `execution_allowed: false` and `execution_permission: not_granted`.
- Backend Capability Coverage v0 with schema at
  `schemas/backend_capability_coverage_report.v0.schema.json`, deterministic
  golden evidence at
  `tests/golden/backend_capability_coverage/current_report.json`, and
  execution-free coverage for `matmul`, `elementwise`, `reduction`, and
  `softmax` across current simulator capability data.
- Runtime readiness and execution-trace goldens for `proof_of_abstraction`,
  `proof_of_reduction`, and `proof_of_softmax`.
- Separate `proof_of_execution` HAC-IR, runtime-plan, and compiler-decision
  goldens.
- Runtime operation semantic contract checks for MVP operation shapes, axes,
  scalar-output rejection, and supported elementwise kernels.
- Runtime graph topology contract checks for unique tensor producers,
  topological operation order, and external-input overwrite rejection before
  trusted kernels run.
- Runtime tensor value contract checks for declared shapes, `float64` dtype,
  and finite values at input and output boundaries.
- Runtime Tensor Store v0 with internal read-only `RuntimeValueRecord` objects
  for accepted input and computed runtime values, including data-only producer
  provenance for external inputs and operation-produced values plus planned
  backend, memory-domain, layout, and placement-source metadata.
- Runtime Tensor Store Evidence v0 with schema at
  `schemas/runtime_tensor_store_evidence_report.v0.schema.json`, deterministic
  golden evidence at
  `tests/golden/runtime_tensor_store_evidence/proof_of_execution.json`, and
  Runtime Evidence Gate coverage with raw tensor values omitted by policy and
  placement metadata checked against the accepted `PartitionPlan`.
- Systolic Runtime Tensor Store Evidence with deterministic golden evidence at
  `tests/golden/runtime_tensor_store_evidence/proof_of_systolic_execution.json`,
  showing planned `systolic-sim`, `device_sram`, and `blocked` value-record
  metadata without raw tensor values.
- Mixed Runtime Tensor Store Evidence with deterministic golden evidence at
  `tests/golden/runtime_tensor_store_evidence/runtime_mixed_backend_equivalence.json`,
  showing the accepted `systolic-sim -> vector-sim -> vector-sim -> vector-sim`
  plan as read-only value-record placement metadata without raw tensor values.
- Runtime Backend Equivalence v0 with schema at
  `schemas/runtime_backend_equivalence_report.v0.schema.json`, deterministic
  golden evidence at
  `tests/golden/runtime_backend_equivalence/current_report.json`, and a
  practical `reference-cpu` versus `systolic-sim` placement comparison for the
  same neutral graph without serialized tensor values.
- Runtime Vector Backend Equivalence evidence at
  `examples/runtime_vector_backend_equivalence.py` with deterministic golden
  evidence at `tests/golden/runtime_backend_equivalence/vector_sim_report.json`,
  proving a `reference-cpu` baseline and `vector-sim` candidate preserve
  terminal output semantics for `softmax -> reduction -> elementwise` without
  serialized tensor values.
- Runtime Evidence Gate now requires and binds Runtime Vector Backend
  Equivalence evidence, verifying the expected `reference-cpu` versus
  `vector-sim` placement sequence and raw-value omission policy in CI-facing
  output.
- Runtime Mixed Backend Equivalence evidence at
  `examples/runtime_mixed_backend_equivalence.py` with deterministic golden
  evidence at
  `tests/golden/runtime_backend_equivalence/mixed_accelerators.json`, proving a
  `reference-cpu` baseline and a `systolic-sim` plus `vector-sim` candidate
  compose in one graph while preserving terminal output semantics without
  serialized tensor values.
- Runtime Evidence Gate now requires and binds Runtime Mixed Backend
  Equivalence evidence, verifying the expected heterogeneous accelerator
  sequence and raw-value omission policy in CI-facing output.
- Runtime Backend Equivalence Portfolio aggregates the systolic, vector, and
  mixed equivalence reports into one backend-diversity evidence artifact and is
  itself bound by Runtime Evidence Gate.
- Runtime Evidence Matrix now includes the Backend Equivalence Portfolio as
  scoped proof-inventory evidence, so backend diversity is visible in the
  matrix rather than only in gate-local checks.
- Runtime Backend Equivalence Portfolio Policy makes the current accepted
  portfolio membership explicit and schema-versioned, preventing silent changes
  to the backend-diversity proof set.
- Runtime Evidence Flow documentation at `docs/RUNTIME_EVIDENCE_FLOW.md`,
  explaining what runs, what is stored, what is public, what is hashed, what is
  never serialized, and which runtime gates must pass.
- Runtime Input Manifest v0 with schema at
  `schemas/runtime_input_manifest_report.v0.schema.json`, deterministic golden
  evidence at `tests/golden/runtime_input_manifest/proof_of_execution.json`,
  and Runtime Evidence Gate coverage for accepted graph external inputs without
  raw tensor values.
- Runtime Output Manifest v0 with schema at
  `schemas/runtime_output_manifest_report.v0.schema.json`, deterministic golden
  evidence at `tests/golden/runtime_output_manifest/proof_of_execution.json`,
  and Runtime Evidence Gate coverage for terminal graph outputs without raw
  tensor values.
- Runtime Reference Correctness v0 with schema at
  `schemas/runtime_reference_correctness_report.v0.schema.json`, deterministic
  golden evidence at
  `tests/golden/runtime_reference_correctness/proof_of_execution.json`, Runtime
  Evidence Gate coverage, and proof-of-execution reporting without raw
  result/reference tensor values.
- Runtime Execution Receipt v0 with schema at
  `schemas/runtime_execution_receipt_report.v0.schema.json`, deterministic
  golden evidence at
  `tests/golden/runtime_execution_receipt/proof_of_execution.json`, linking
  tensor-store, input-manifest, output-manifest, output-contract,
  public-output-bundle, and reference-correctness evidence by metadata digest
  without raw tensor values.
- Runtime Execution Evidence Bundle v0 with schema at
  `schemas/runtime_execution_evidence_bundle_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/runtime_execution_evidence_bundle/proof_of_execution.json`,
  packaging tensor-store, input-manifest, output-manifest, output-contract,
  public-output-bundle, reference-correctness, and execution-receipt reports
  into one metadata-only review artifact.
- Runtime Execution Evidence Bundle Binding in Runtime Evidence Gate, rejecting
  stale or forged bundles whose embedded graph names, contracts, metadata
  digests, item counts, pass status, or raw-value policy do not match the
  evidence reports evaluated by the same gate invocation, with the decision
  captured in
  `rfcs/0130-runtime-evidence-gate-execution-bundle-binding.md`.
- Runtime Execution Output Closure v0 binds proof-of-execution Output Contract
  and Runtime Public Output Bundle evidence into Runtime Execution Receipt and
  Runtime Execution Evidence Bundle, with the decision captured in
  `rfcs/0204-runtime-execution-output-closure.md`.
- Runtime Execution Output Closure Report v0 with schema at
  `schemas/runtime_execution_output_closure_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/runtime_execution_output_closure/proof_of_execution.json`,
  multi-output closure evidence at
  `tests/golden/runtime_execution_output_closure/multi_output_execution.json`,
  softmax closure evidence at
  `tests/golden/runtime_execution_output_closure/proof_of_softmax.json`,
  and Runtime Evidence Gate binding, with the decisions captured in
  `rfcs/0205-runtime-execution-output-closure-report.md`,
  `rfcs/0207-runtime-multi-output-execution-output-closure.md`, and
  `rfcs/0208-runtime-softmax-execution-output-closure.md`.
- Runtime Evidence Replay Verifier v0 with schema at
  `schemas/runtime_evidence_replay_verifier_report.v0.schema.json`, example at
  `examples/runtime_evidence_replay_verifier.py`, deterministic golden evidence
  at `tests/golden/runtime_evidence_replay_verifier/proof_of_execution.json`,
  and RFC at `rfcs/0210-runtime-evidence-replay-verifier.md`.
- Runtime Execution Receipt Binding in Runtime Evidence Gate, rejecting receipts
  whose graph names, contracts, metadata digests, item counts, pass status, or
  raw-value policy do not match the evidence reports evaluated by the same gate
  invocation, with the decision captured in
  `rfcs/0128-runtime-execution-receipt-gate-binding.md`.
- Runtime Multi-Output Evidence fixture with deterministic golden evidence at
  `tests/golden/runtime_multi_output_evidence/current_report.json`, proving
  Runtime Output Manifest and Runtime Reference Correctness across two terminal
  graph outputs without raw tensor values.
- Runtime Output Contract v0 with schema at
  `schemas/runtime_output_contract_report.v0.schema.json`, deterministic golden
  evidence at `tests/golden/runtime_output_contract/current_report.json`, and
  explicit public output aliases for terminal graph tensors without raw tensor
  values.
- Runtime Public Output Bundle v0 with schema at
  `schemas/runtime_public_output_bundle_report.v0.schema.json`, deterministic
  golden evidence at
  `tests/golden/runtime_public_output_bundle/current_report.json`, and
  read-only public-name-to-runtime-value mapping while review evidence remains
  metadata-only.
- Runtime Evidence Gate now requires Runtime Input Manifest, Runtime Execution
  Receipt, Runtime Execution Evidence Bundle, Runtime Output Contract, and
  Runtime Public Output Bundle evidence in addition to Runtime Evidence Matrix,
  Runtime Executor Conformance, Runtime Tensor Store Evidence, Runtime Output
  Manifest, and Runtime Reference Correctness.
- Runtime Evidence Matrix now treats `output_contract` as required graph
  evidence, aligning the curated proof inventory with the Runtime Evidence Gate
  contract, with the decision captured in
  `rfcs/0113-runtime-evidence-matrix-output-contract.md`.
- Runtime Evidence Matrix now treats `public_output_bundle` as required graph
  evidence, aligning curated proof inventory with the read-only public runtime
  return boundary, with the decision captured in
  `rfcs/0115-runtime-evidence-public-output-bundle.md`.
- Runtime Evidence Matrix now treats `input_manifest` as required graph
  evidence, aligning accepted external runtime inputs with Runtime Evidence
  Gate coverage and `schemas/runtime_input_manifest_report.v0.schema.json`,
  with the decision captured in
  `rfcs/0125-runtime-evidence-matrix-input-manifest.md`.
- Runtime Evidence Matrix now treats `tensor_store_evidence` as required graph
  evidence, aligning planned runtime value-record placement metadata with graph
  evidence completeness and
  `schemas/runtime_tensor_store_evidence_report.v0.schema.json`, with the
  decision captured in
  `rfcs/0135-runtime-evidence-matrix-tensor-store-evidence.md`.
- Runtime Evidence Matrix now treats `execution_receipt` as required graph
  evidence, aligning linked runtime execution evidence with Runtime Evidence
  Gate coverage and
  `schemas/runtime_execution_receipt_report.v0.schema.json`, with the decision
  captured in `rfcs/0127-runtime-evidence-matrix-execution-receipt.md`.
- Source Intent Return Semantics v0 with optional `returns` in
  `schemas/source_intent.v0.schema.json`, deterministic golden evidence at
  `tests/golden/frontend/source_intent_return_semantics_report.txt`, and
  execution-free public-name-to-terminal-tensor intent before Runtime Output
  Contract evidence is built, documented in
  `docs/SOURCE_INTENT_RETURN_SEMANTICS.md`.
- Source Intent Runtime Returns v0 with schema at
  `schemas/source_intent_runtime_returns_report.v0.schema.json`, deterministic
  golden evidence at
  `tests/golden/frontend/source_intent_runtime_returns_report.json`, and
  explicit proof that frontend return intent resolves through Runtime Output
  Contract and Runtime Public Output Bundle after trusted prototype execution,
  documented in `docs/SOURCE_INTENT_RUNTIME_RETURNS.md`.
- Runtime Evidence Matrix now inventories `source_intent_return_mlp` as a
  complete Source Intent metadata graph with Source Intent return semantics and
  Source Intent Runtime Returns evidence.
- Runtime Evidence Gate now requires Source Intent Runtime Returns evidence in
  addition to matrix, executor conformance, tensor store, input manifest,
  output manifest, output contract, public output bundle, reference correctness,
  and execution receipt evidence.
- Runtime Evidence Gate now binds Source Intent Runtime Returns to the curated
  `source_intent_return_mlp` Runtime Evidence Matrix graph, failing closed when
  the matrix graph, source boundary, required Source Intent artifacts, or report
  graph name drift.
- Runtime Evidence Gate now requires Runtime Backend Equivalence evidence and
  binds it to the expected `reference_cpu` baseline versus `systolic_sim`
  candidate placement, failing closed on graph, run ID, backend-sequence,
  comparison-status, or raw-value-policy drift.
- Source Intent Frontend Conformance now includes explicit public-return
  fixtures, return-alias preservation checks, and fail-closed rejected cases for
  unknown, intermediate, and duplicate public returns.
- Source Intent Frontend Conformance Gate now enforces the conformance suite and
  required public-return coverage as CI-facing merge evidence, with deterministic
  golden output at
  `tests/golden/frontend/source_intent_frontend_conformance_gate.txt`.
- Source-To-Intent Readiness now requires
  `source_intent_frontend_conformance_gate`, keeping future parser proposals
  blocked unless frontend conformance and public-return coverage pass the
  merge-facing gate.
- Source-To-Intent Parser Block Gate now asserts in CI that the default
  source-to-intent parser path remains blocked, with deterministic golden
  output at `tests/golden/frontend/source_to_intent_parser_block_gate.txt`.
- Source-To-Intent Research Readiness now tracks the first narrow parser
  research proposal separately from the default block gate, showing current
  proposal evidence complete while keeping the default parser path blocked.
- Source-To-Intent Corpus Evidence now adds accepted and rejected source-buffer


  in accepted cases while keeping source text disconnected from Source Intent
  IR and compiler artifacts.
- Source-To-Intent Property Corpus now binds fuzz/property obligations to the
  source corpus report digest, marking `source_fuzz_or_property_corpus` present
  while default parser intake remains blocked.
- Source-To-Intent Parser Report now adds the proposal-only parser report
  golden, completing research-readiness evidence while explicitly keeping
  `parser_enabled = false` and implementation status `not_implemented`.
- Source-To-Intent Research Parser now adds the first explicit source-buffer to
  `source_intent.v0` implementation slice for a tiny Triton-like subset, with a
  schema-versioned metadata-only report and deterministic golden evidence while
  keeping metadata, `ComputeGraph`, IR, runtime-plan, and backend-decision
  outputs blocked.
- Source-To-Intent Research Parser Conformance Gate now binds the
  `matmul -> elementwise` parser output slice to Source Intent Frontend
  Conformance, with deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_parser_conformance_gate.txt`
  and CI coverage in the `python` workflow job.
- Source Intent axis attributes now carry neutral `axis` semantics for
  `softmax` and `reduction` through Source Intent Intake, Metadata Conversion,
  and Research Parser Conformance Gate evidence without introducing backend,
  device, or placement facts.
- Source Intent Axis Attributes are documented at
  `docs/SOURCE_INTENT_AXIS_ATTRIBUTES.md` and accepted by
  `rfcs/0157-source-intent-axis-attributes.md`.
- Source-To-Intent Research Diagnostics now checks the accepted research parser


  reason IDs, deterministic golden evidence, and CI coverage.
- Source-To-Intent Research Evidence Gate now binds Research Readiness,
  Research Parser Conformance Gate, and Research Diagnostics by SHA-256 digest,
  making the accepted parser proof scope CI-facing and drift-resistant.
- Source-To-Intent Research Execution Bridge now proves accepted parser output
  can re-enter Source Intent Intake and reach controlled Runtime Executor plus
  Runtime Reference Correctness evidence without parser compiler shortcuts or
  raw tensor values.

## In Progress

### Phase Alpha: Smallest Unarguable Proof

Current slice:

- Explicit `tlir`, `hac-ir`, and `hs-ir` module stages.
- TLIR -> HAC-IR lowering.
- HAC-IR -> HS-IR lowering with backend assignments.
- Stable text dumps for debugging and tests.
- Early TLIR/HAC-IR/HS-IR vertical-slice example.
- MVP kernel family definition.
- Triton compatibility matrix.
- Data-movement-aware HAC-IR annotations for MVP kernels.
- HS-IR movement summaries for future runtime planning.
- Secure IR validation and immutable metadata baseline.
- Backend capability validation and memory-domain metadata.
- Transfer-byte-aware partition plan diagnostics.
- Apache-2.0 license and initial supply-chain security workflows.
- Explicit runtime transfer-edge objects.
- Runtime layout-conversion costing.
- Backend layout capability schema.
- Runtime transfer bandwidth, latency, and energy estimates.
- Stable runtime plan dump.
- Backend produced-layout schema.
- Validated in-memory transfer-cost profiles.
- Runtime plan golden dumps.
- Schema-versioned backend manifest files.
- Calibrated transfer-cost profile files.
- Golden-kernel correctness suite.
- Prototype frontend adapter for Triton-like kernel metadata.
- Schema-versioned Triton metadata intake contract with execution-surface
  rejection and deterministic intake reports.
- Triton metadata frontend golden artifacts for intake report, HAC-IR,
  runtime-plan, and compiler decision-report review.
- Triton metadata MVP family coverage for `matmul`, `softmax`, `reduction`,
  and `elementwise` in one execution-free frontend-originated graph.
- Machine-readable Triton idiom coverage report at
  `schemas/triton_idiom_coverage_report.v0.schema.json` for tracking metadata
  examples, intake goldens, HAC-IR goldens, runtime-plan goldens, and compiler
  decision goldens without source parsing.
- Deterministic Triton idiom coverage golden at
  `tests/golden/frontend/triton_idiom_coverage_report.json`.
- Runtime Executor v0 with contract `runtime_executor.trusted_backend.v0`,
  fixed trusted registry `trusted_runtime_executor_registry.v0`, plain-mapping
  input validation, partition-plan matching, graph-topology checks,
  output-shape checks, unsupported executor rejection, internal
  `RuntimeValueRecord` storage, and deterministic execution traces.
- Runtime Tensor Store Evidence at `examples/runtime_tensor_store_evidence.py`,
  with golden evidence at
  `tests/golden/runtime_tensor_store_evidence/proof_of_execution.json`,
  including producer-kind, producer-id, and planned placement metadata without
  tensor values.
- Systolic Runtime Tensor Store Evidence at
  `examples/runtime_systolic_tensor_store_evidence.py`, with golden evidence at
  `tests/golden/runtime_tensor_store_evidence/proof_of_systolic_execution.json`.
- Runtime Backend Equivalence at `examples/runtime_backend_equivalence.py`,
  with golden evidence at
  `tests/golden/runtime_backend_equivalence/current_report.json`.
- Runtime Vector Backend Equivalence at
  `examples/runtime_vector_backend_equivalence.py`, with golden evidence at
  `tests/golden/runtime_backend_equivalence/vector_sim_report.json`.
- Runtime Mixed Backend Equivalence at
  `examples/runtime_mixed_backend_equivalence.py`, with golden evidence at
  `tests/golden/runtime_backend_equivalence/mixed_accelerators.json`.
- Mixed Runtime Tensor Store Evidence at
  `examples/runtime_mixed_tensor_store_evidence.py`, with golden evidence at
  `tests/golden/runtime_tensor_store_evidence/runtime_mixed_backend_equivalence.json`.
- Runtime Input Manifest at `examples/runtime_input_manifest.py`, with golden
  evidence at `tests/golden/runtime_input_manifest/proof_of_execution.json`,
  including accepted external-input metadata without tensor values.
- Runtime Output Manifest at `examples/runtime_output_manifest.py`, with golden
  evidence at `tests/golden/runtime_output_manifest/proof_of_execution.json`,
  including terminal-output producer metadata without tensor values.
- Runtime Reference Correctness at `examples/runtime_reference_correctness.py`,
  with golden evidence at
  `tests/golden/runtime_reference_correctness/proof_of_execution.json`,
  including output/reference comparison status without tensor values.
- Runtime Execution Receipt at `examples/runtime_execution_receipt.py`, with
  golden evidence at
  `tests/golden/runtime_execution_receipt/proof_of_execution.json`, linking
  runtime evidence digests, public output metadata, and operation trace metadata
  without tensor values.
- Runtime Execution Evidence Bundle at
  `examples/runtime_execution_evidence_bundle.py`, with golden evidence at
  `tests/golden/runtime_execution_evidence_bundle/proof_of_execution.json`,
  embedding the receipt, public output reports, and runtime evidence reports as
  one metadata-only review package.
- Runtime Multi-Output Evidence at `examples/runtime_multi_output_evidence.py`,
  with golden evidence at
  `tests/golden/runtime_multi_output_evidence/current_report.json`, covering
  branched terminal outputs without tensor values.
- Runtime Output Contract at `examples/runtime_output_contract.py`, with golden
  evidence at `tests/golden/runtime_output_contract/current_report.json`,
  separating public output aliases from terminal graph tensor names.
- Runtime Public Output Bundle at `examples/runtime_public_output_bundle.py`,
  with golden evidence at
  `tests/golden/runtime_public_output_bundle/current_report.json`, resolving
  public aliases to read-only runtime values without serializing tensor values
  into review artifacts.
- Source Intent Return Semantics at
  `examples/source_intent_return_semantics.py`, with golden evidence at
  `tests/golden/frontend/source_intent_return_semantics_report.txt`, connecting
  frontend public output intent to Runtime Output Contract aliases
  without source parsing or runtime execution.
- Source Intent Runtime Returns at `examples/source_intent_runtime_returns.py`,
  with golden evidence at
  `tests/golden/frontend/source_intent_runtime_returns_report.json`, proving
  explicit frontend return aliases resolve through Runtime Output Contract and
  Runtime Public Output Bundle after trusted prototype execution.
- Proof-of-execution golden at `tests/golden/proofs/proof_of_execution.txt` and
  execution-trace golden at
  `tests/golden/execution_traces/proof_of_execution.txt`.
- Triton metadata MVP-family execution trace golden at
  `tests/golden/execution_traces/triton_metadata_mvp_families.txt`.
- Trusted runtime backend contract golden at
  `tests/golden/runtime_backend_contracts/trusted_runtime_executor_registry.txt`.
- Runtime execution readiness golden at
  `tests/golden/execution_readiness/proof_of_execution.txt`.
- Triton metadata MVP-family readiness golden at
  `tests/golden/execution_readiness/triton_metadata_mvp_families.txt`.
- Runtime Evidence Matrix report at
  `schemas/runtime_evidence_matrix_report.v0.schema.json`, with golden evidence
  at `tests/golden/proofs/runtime_evidence_matrix_report.json`, now including
  scoped backend-equivalence graph entries.
- Runtime Executor Conformance report at
  `schemas/runtime_executor_conformance_report.v0.schema.json`, with golden
  evidence at
  `tests/golden/runtime_executor_conformance/trusted_runtime_executor_registry.json`.
- Runtime Evidence Gate at `examples/runtime_evidence_gate.py`, with golden
  evidence at `tests/golden/proofs/runtime_evidence_gate.txt`, now composing
  Runtime Evidence Matrix, Runtime Executor Conformance, Runtime Backend
  Equivalence, Runtime Planning Explanation, Runtime Vector Backend
  Equivalence, Runtime Mixed Backend Equivalence, Runtime Tensor Store
  Evidence, Runtime Input Manifest, Runtime Output Manifest, Runtime Output
  Contract, Runtime Public Output Bundle,
  Runtime Reference Correctness, Runtime Execution Receipt, Runtime Execution
  Evidence Bundle, Runtime Execution Output Closure,
  proof-of-execution public-output closure, and Source Intent Runtime Returns,
  with binding checks for
  the backend-equivalence fixture and the `source_intent_return_mlp` frontend
  fixture.
- Runtime Candidate Score Evidence at
  `examples/runtime_candidate_score_evidence.py`, with golden evidence at
  `tests/golden/runtime_candidate_score_evidence/profiled_candidate_score_report.json`.
- Runtime Planning Explanation at
  `examples/runtime_planning_explanation.py` and
  `examples/runtime_mixed_planning_explanation.py`, with golden evidence at
  `tests/golden/runtime_planning_explanation/systolic_report.json` and
  `tests/golden/runtime_planning_explanation/mixed_backend_equivalence_report.json`,
  plus Runtime Evidence Gate binding for the backend-equivalence planning
  slices.
- Runtime Candidate Scoring Policy at
  `examples/runtime_candidate_scoring_policy.py`, with golden evidence at
  `tests/golden/runtime_candidate_scoring_policy/current_policy_report.json`.
- Runtime Candidate Scoring Conformance at
  `examples/runtime_candidate_scoring_conformance.py`, with golden evidence at
  `tests/golden/runtime_candidate_scoring_conformance/current_conformance_report.json`.
- Runtime Candidate Scoring Gate at `examples/runtime_candidate_scoring_gate.py`,
  with golden evidence at
  `tests/golden/runtime_candidate_scoring_gate/current_gate.txt`.
- Runtime Buffer Lifetime at `examples/runtime_buffer_lifetime.py`, with golden
  evidence at `tests/golden/runtime_buffer_lifetime/current_report.json`,
  exposing `lifetime_metadata_digest`.
- Runtime Allocation Plan at `examples/runtime_allocation_plan.py`, with golden
  evidence at `tests/golden/runtime_allocation_plan/current_report.json`,
  bound to the source Buffer Lifetime metadata digest and exposing
  `allocation_metadata_digest` for downstream binding.
- Runtime Memory Budget at `examples/runtime_memory_budget.py`, with golden
  evidence at `tests/golden/runtime_memory_budget/current_report.json`, bound
  to the source Allocation Plan metadata digest.
- Runtime Allocation Request Manifest at
  `examples/runtime_allocation_request_manifest.py`, with golden evidence at
  `tests/golden/runtime_allocation_request_manifest/current_report.json`,
  exposing bounded future allocator requests without runtime handles.
- Runtime Allocation Admission at `examples/runtime_allocation_admission.py`,
  with schema at `schemas/runtime_allocation_admission_report.v0.schema.json`
  and golden evidence at
  `tests/golden/runtime_allocation_admission/current_report.json`, admitting
  only requests that match current Memory Budget evidence without runtime
  handles.
- Runtime Allocation Receipt at `examples/runtime_allocation_receipt.py`, with
  schema at `schemas/runtime_allocation_receipt_report.v0.schema.json` and
  golden evidence at
  `tests/golden/runtime_allocation_receipt/current_report.json`, recording
  deterministic dry-run allocation ledger entries without pointers or handles.
- Runtime Memory Planning Gate at `examples/runtime_memory_planning_gate.py`,
  with golden evidence at
  `tests/golden/runtime_memory_planning_gate/current_gate.txt`, rejecting stale
  Allocation Plan evidence whose source Buffer Lifetime digest does not match,
  stale Memory Budget evidence whose source Allocation Plan digest does not
  match, stale Allocation Request Manifest evidence whose source Allocation
  Plan or Memory Budget binding does not match, stale Allocation Admission
  evidence whose Request Manifest or Memory Budget binding does not match, and
  stale Allocation Receipt evidence whose Allocation Admission binding does not
  match.
- Systolic simulator proof at `examples/proof_of_systolic_execution.py`, with
  evidence goldens under `tests/golden/proofs/`,
  `tests/golden/hac_ir/`, `tests/golden/runtime_plans/`,
  `tests/golden/compiler_decisions/`, `tests/golden/execution_readiness/`, and
  `tests/golden/execution_traces/`.
- Systolic capability manifest at
  `examples/manifests/systolic_sim_backend.json` and manifest-loaded proof at
  `examples/systolic_manifest_path.py`, with deterministic golden evidence at
  `tests/golden/proofs/systolic_manifest_path.txt`.
- Proof-of-execution independent evidence goldens at
  `tests/golden/hac_ir/proof_of_execution.txt`,
  `tests/golden/runtime_plans/proof_of_execution.txt`, and
  `tests/golden/compiler_decisions/proof_of_execution.txt`.
- Objective Alpha proof readiness goldens at
  `tests/golden/execution_readiness/proof_of_abstraction.txt`,
  `tests/golden/execution_readiness/proof_of_reduction.txt`, and
  `tests/golden/execution_readiness/proof_of_softmax.txt`.
- Objective Alpha proof execution-trace goldens at
  `tests/golden/execution_traces/proof_of_abstraction.txt`,
  `tests/golden/execution_traces/proof_of_reduction.txt`, and
  `tests/golden/execution_traces/proof_of_softmax.txt`.
- Runtime Executor negative tests for input shape mismatch, non-`float64`
  inputs, non-finite inputs, and non-finite outputs.
- Runtime Executor negative tests for non-topological graph order, duplicate
  output tensor definitions, and external-input overwrite attempts.
- Runtime Executor negative tests for matmul dimension mismatch, elementwise
  output mismatch, unsupported elementwise kernels, reduction axis/output
  errors, scalar reduction output, and softmax axis/output errors.
- Triton source threat model that blocks direct source parsing and `@triton.jit`
  handling until parser budgets, negative tests, fuzzing, diagnostics, and
  sandboxing gates exist.
- Triton source preflight v0 with execution-free source budgets, negative
  tests, deterministic report golden, and no source-to-IR conversion.
- Triton source preflight fuzz/property corpus for arbitrary decoded bytes,
  invalid Unicode, seed combinations, bounded diagnostics, and known malicious
  source surfaces.
- Canonical Source Intent IR v0 as a data-only frontend contract with
  deterministic dump, negative hardware-leakage tests, and no metadata or
  compiler-lowering exit.
- Source Intent Intake v0 for schema-versioned plain-data construction of
  `SourceIntentModule`, with fail-closed unknown-key and source-text rejection
  plus deterministic frontend goldens.
- Machine-readable Source Intent JSON Schema at
  `schemas/source_intent.v0.schema.json` for external frontend authors.
- Source Intent Frontend Conformance fixtures with deterministic JSON report
  artifacts for external frontend authors that emit `source_intent.v0` plain
  data, including explicit public-return fixtures and rejected malformed return
  cases.
- Source Intent Frontend Conformance Gate at
  `examples/source_intent_frontend_conformance_gate.py`, with golden evidence at
  `tests/golden/frontend/source_intent_frontend_conformance_gate.txt` and CI
  coverage in the `python` workflow job.
- Machine-readable Source Intent Frontend Conformance report JSON Schema at
  `schemas/source_intent_frontend_conformance_report.v0.schema.json`.
- Source-To-Intent Parser Gate defining the required future parser RFC,
  budgets, accepted/rejected corpus, deterministic diagnostics, goldens,
  HAC-IR neutrality review, and conformance evidence before source text may
  create `source_intent.v0` plain data.
- Source-To-Intent Readiness report with deterministic blocked golden evidence
  for future parser proposals, now requiring Source Intent Frontend Conformance
  Gate evidence before source text can influence compiler artifacts.
- Source-To-Intent Parser Block Gate at
  `examples/source_to_intent_parser_block_gate.py`, with golden evidence at
  `tests/golden/frontend/source_to_intent_parser_block_gate.txt` and CI
  coverage in the `python` workflow job.
- Source-To-Intent Research Readiness at
  `examples/source_to_intent_research_readiness.py`, with golden evidence at
  `tests/golden/frontend/source_to_intent_research_readiness.json`, tracking
  complete proposal-readiness evidence while the default parser path remains
  blocked.
- Source-To-Intent Corpus Evidence at `examples/source_to_intent_corpus.py`,
  with fixtures under `tests/corpus/source_to_intent_parser/` and golden
  evidence at `tests/golden/frontend/source_to_intent_corpus_report.json`.
- Source-To-Intent Property Corpus at
  `examples/source_to_intent_property_corpus.py`, with golden evidence at
  `tests/golden/frontend/source_to_intent_property_corpus_report.json`.
- Source-To-Intent Parser Report at `examples/source_to_intent_parser_report.py`,
  with golden evidence at
  `tests/golden/frontend/source_to_intent_parser_report.json`.
- Source-To-Intent Research Parser at
  `examples/source_to_intent_research_parser.py`, with schema at
  `schemas/source_to_intent_research_parser_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_parser.json`, and


  unsupported assignments, shape mismatches, and unknown shape manifest entries.
- Source-To-Intent Research Parser Conformance Gate at
  `examples/source_to_intent_research_parser_conformance_gate.py`, with golden
  evidence at
  `tests/golden/frontend/source_to_intent_research_parser_conformance_gate.txt`.
- Source-To-Intent Research Diagnostics at
  `examples/source_to_intent_research_diagnostics.py`, with schema at
  `schemas/source_to_intent_research_diagnostics_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_diagnostics_report.json`,
  and source-free rejection reason IDs for accepted/rejected parser cases, including annotated-signature rejection.
- Source-To-Intent Research Preflight Bridge at
  `examples/source_to_intent_research_preflight_bridge.py`, with schema at
  `schemas/source_to_intent_research_preflight_bridge_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_preflight_bridge.json`, and
  digest binding through Source-To-Intent Research Evidence Gate.
- Source-To-Intent Research Evidence Gate at
  `examples/source_to_intent_research_evidence_gate.py`, with deterministic
  golden evidence at
  `tests/golden/frontend/source_to_intent_research_evidence_gate.txt`, binding
  readiness, conformance, and diagnostics by SHA-256 digest.
- Source-To-Intent Research Execution Bridge at
  `examples/source_to_intent_research_execution_bridge.py`, with schema at
  `schemas/source_to_intent_research_execution_bridge_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_execution_bridge.json`, and
  digest binding through Source-To-Intent Research Evidence Gate.
- Source-To-Intent Research Idiom Alignment at
  `examples/source_to_intent_research_idiom_alignment.py`, with schema at
  `schemas/source_to_intent_research_idiom_alignment_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_idiom_alignment.json`, and
  digest binding through Source-To-Intent Research Evidence Gate.
- Source-To-Intent Research Proof Bundle at
  `examples/source_to_intent_research_proof_bundle.py`, with schema at
  `schemas/source_to_intent_research_proof_bundle_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_proof_bundle.json`, and
  digest-only review binding for the current source-to-runtime research proof.
- Source-To-Intent Research Capability Claim at
  `examples/source_to_intent_research_capability_claim.py`, with schema at
  `schemas/source_to_intent_research_capability_claim_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_capability_claim.json`, and
  a digest-only supported-claim boundary for the current bounded Universal
  Compute research slice.
- Source-To-Intent Research Capability Claim Gate at
  `examples/source_to_intent_research_capability_claim_gate.py`, with
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_capability_claim_gate.txt`,
  exact evidence-ID binding for the thirteen claim-supporting artifacts, and
  CI-facing binding for the current supported claim boundary.
- Source-To-Intent Research Source Runtime Smoke at
  `examples/source_to_intent_research_source_runtime_smoke.py`, with schema at
  `schemas/source_to_intent_research_source_runtime_smoke_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_source_runtime_smoke.json`,
  and digest binding through Source-To-Intent Research Evidence Gate and Proof
  Bundle.
- Source-To-Intent Research Kernel Ingress at
  `examples/source_to_intent_research_kernel_ingress.py`, with frontend API at
  `src/tuc/frontend/source_to_intent_research_kernel_ingress.py`, schema at
  `schemas/source_to_intent_research_kernel_ingress_e2e_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress.json`, and
  digest binding through Source-To-Intent Research Evidence Gate and Proof
  Bundle for realistic Triton module-shaped source buffers.
- Source-To-Intent Research Kernel Ingress Fixture Expansion adds
  `matmul_reduction` as a third accepted module-shaped case, with coverage in
  runtime matrix, runtime coverage policy, backend alignment, diagnostics,
  conformance, proof bundle, and evidence gates.
- Source-To-Intent Research Kernel Ingress Combined MVP Pipeline adds
  `mvp_pipeline` as a fourth accepted module-shaped case covering
  `matmul -> softmax -> reduction -> elementwise`, with a four-step trusted
  runtime sequence and coverage in runtime matrix, runtime coverage policy,
  backend alignment, diagnostics, conformance, proof bundle, and evidence
  gates.
- Source-To-Intent Research Kernel Ingress Runtime Matrix at
  `examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`, with
  schema at
  `schemas/source_to_intent_research_kernel_ingress_runtime_matrix_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_matrix.json`,
  backend-sequence and trace-step inventory for accepted Kernel Ingress cases,
  and binding through the Kernel Ingress Proof Bundle and focused Evidence
  Gate.
- Source-To-Intent Research Kernel Ingress Runtime Step Trace at
  `examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py`,
  with schema at
  `schemas/source_to_intent_research_kernel_ingress_runtime_step_trace_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_step_trace.json`,
  operation-level planned/executed backend trace metadata for accepted Kernel
  Ingress cases, and binding through the Kernel Ingress Proof Bundle, focused
  Evidence Gate, and Capability Claim.
- Source-To-Intent Research Kernel Ingress Runtime Evidence Bundle Index at
  `examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`,
  with schema at
  `schemas/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.json`,
  digest-only bindings from accepted Kernel Ingress cases to standard Runtime
  Execution Evidence Bundle sections, and binding through the Kernel Ingress
  Proof Bundle, focused Evidence Gate, and Capability Claim.
- Source-To-Intent Research Kernel Ingress Runtime Output Closure Index at
  `examples/source_to_intent_research_kernel_ingress_runtime_output_closure_index.py`,
  with schema at
  `schemas/source_to_intent_research_kernel_ingress_runtime_output_closure_index_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_output_closure_index.json`,
  digest-only bindings from accepted Kernel Ingress cases to Runtime Execution
  Output Closure, and binding through the Kernel Ingress Proof Bundle, focused
  Evidence Gate, and Capability Claim.
- Source-To-Intent Research Kernel Ingress Runtime Replay Verifier Index at
  `examples/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py`,
  with schema at
  `schemas/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.json`,
  digest-only replay bindings from serialized Runtime Evidence Bundle and
  Output Closure reports, and binding through the Kernel Ingress Proof Bundle,
  focused Evidence Gate, and Capability Claim.
- Source-To-Intent Research Kernel Ingress Backend Equivalence at
  `examples/source_to_intent_research_kernel_ingress_backend_equivalence.py`,
  with schema at
  `schemas/source_to_intent_research_kernel_ingress_backend_equivalence_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_backend_equivalence.json`,
  metadata-only `reference-cpu` baseline versus capability-selected
  `linear-sim`/`vector-sim` runtime equivalence evidence, and binding through
  the Kernel Ingress Proof Bundle, focused Evidence Gate, and Capability
  Claim.
- Source-To-Intent Research Kernel Ingress Backend Equivalence Shape Profiles
  at
  `examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py`,
  with schema at
  `schemas/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.json`,
  metadata-only `reference-cpu` baseline versus capability-selected
  `linear-sim`/`vector-sim` equivalence evidence across `base` and
  `alternate` declared tensor shape profiles, reference-correctness digests
  for both placements, and binding through the Kernel Ingress Proof Bundle,
  focused Evidence Gate, and Capability Claim.
- Source-To-Intent Research Kernel Ingress Workload Scope at
  `examples/source_to_intent_research_kernel_ingress_workload_scope.py`,
  with schema at
  `schemas/source_to_intent_research_kernel_ingress_workload_scope_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_workload_scope.json`,
  a digest-bound bridge from Kernel Ingress shape-profile evidence to
  diagnostic `workload_scope_report.v0` data, 20 bounded workload scopes, and
  native performance claims still blocked.
- Performance Proof Readiness now derives `performance_proof_rfc`,
  `performance_claim_threshold_policy`, and
  `performance_acceptance_criteria` from accepted, digest-pinned governance
  reports for every accepted Kernel Ingress workload scope, while benchmark
  artifacts, executable-surface review, and native performance claims remain
  separate gates.
- Performance Proof Readiness now derives current `workload_scope` and
  `planner_overhead_report` evidence from Kernel Ingress contracts: the
  shape-profile-derived workload scope must pass its contract, and the accepted
  MVP pipeline graph must produce a bounded planner-overhead report that keeps
  execution timing and break-even evidence blocked.
- Performance Proof Readiness now also derives `correctness_goldens`,
  `runtime_plan_goldens`, and `compiler_decision_report_goldens` from the
  deterministic Kernel Ingress golden, requiring the generated report to match
  the golden and each accepted case to expose the matching SHA-256 digest field.
- Performance Proof Readiness now derives `benchmark_report_schema` from the
  baseline benchmark report schema contract, requiring the schema to remain
  fail-closed, diagnostic-only, native-claim-blocked, and bound to the
  performance proof boundary.
- Performance Proof Readiness now derives `benchmark_report_artifacts` from a
  complete Benchmark Artifact Manifest over digest-pinned repository-golden
  descriptors for every required artifact kind, while artifact loading, timing
  validation, and native performance claims remain blocked.
- Performance Proof Readiness now derives `benchmark_methodology` from accepted
  Kernel Ingress workload scopes, requiring bounded measurement-policy entries
  while benchmark execution, raw timing samples, and benchmark artifacts remain
  missing.
- Performance Proof Readiness now derives `versioned_toolchain_environment`
  from a bounded Toolchain Environment Report over repository-controlled CI,
  dependency, Docker, compiler, and compose declarations with SHA-256 digests;
  host discovery, environment capture, and device inspection remain blocked.
- Performance Proof Readiness now derives `native_baseline_provenance` from
  bounded native baseline candidates for every accepted Kernel Ingress workload
  scope, while native reproduction, artifact digests, comparison evidence, and
  native performance claims remain blocked.
- Performance Proof Readiness now derives `native_baseline_comparison` from
  bounded comparison references for every accepted Kernel Ingress workload
  scope, while benchmark artifact loading, digest validation, timing
  comparison, and native performance claims remain blocked.
- Performance Proof Readiness now derives `break_even_workload_size` from
  bounded `estimated_not_validated` amortization entries for every accepted
  Kernel Ingress workload scope, while CI validation, evidence digests,
  benchmark artifact loading, timing comparison, and planner-benefit claims
  remain blocked.
- Performance Proof Readiness now derives `leaky_abstraction_report` from the
  accepted Kernel Ingress MVP pipeline, requiring contract-valid HAC-IR, no
  forbidden hardware-specific HAC-IR attributes, and performance facts assigned
  outside HAC-IR.
- Performance Proof Readiness now derives `executable_backend_security_review`
  from a complete Executable Backend Security Review Report over every tracked
  executable surface, with digest-bound threat-model, sandbox, budget,
  provenance, and negative-test metadata while execution permission and native
  performance claims remain blocked.
- Performance Proof Interpretation now records the post-readiness gate: current
  Kernel Ingress readiness is metadata-complete, but measurement interpretation
  artifacts are not supplied and native performance claims remain blocked.
- Planner Overhead Portfolio at `examples/planner_overhead_portfolio.py`, with
  schema at `schemas/planner_overhead_portfolio_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/proofs/planner_overhead_portfolio_report.json`, and
  documentation at `docs/PLANNER_OVERHEAD_PORTFOLIO.md`, now binds the
  diagnostic planner-overhead phase contract to all accepted Kernel Ingress
  research cases while omitting raw duration values and keeping execution,
  break-even, and native performance claims blocked.
- Source-To-Intent Research Kernel Ingress Runtime Coverage Policy at
  `examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`,
  with schema at
  `schemas/source_to_intent_research_kernel_ingress_runtime_coverage_policy_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_coverage_policy.json`,
  required backend-sequence, terminal-output, trace-step, and runtime-digest
  coverage for accepted Kernel Ingress cases, and binding through the Kernel
  Ingress Proof Bundle and focused Evidence Gate.
- Source-To-Intent Research Kernel Ingress Runtime Backend Alignment at
  `examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`,
  with schema at
  `schemas/source_to_intent_research_kernel_ingress_runtime_backend_alignment_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_runtime_backend_alignment.json`,
  trusted Runtime Executor conformance binding for `linear-sim` and
  `vector-sim`, and binding through the Kernel Ingress Proof Bundle and
  focused Evidence Gate.
- Source-To-Intent Research Kernel Ingress Boundary Budget at
  `examples/source_to_intent_research_kernel_ingress_boundary_budget.py`, with
  schema at
  `schemas/source_to_intent_research_kernel_ingress_boundary_budget_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_boundary_budget.json`,
  budget overflow rejection evidence, and binding through the Kernel Ingress
  Proof Bundle for resource-exhaustion review.
- Source-To-Intent Research Kernel Ingress Rejection Coverage at
  `examples/source_to_intent_research_kernel_ingress_rejection_coverage.py`,
  with schema at
  `schemas/source_to_intent_research_kernel_ingress_rejection_coverage_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_rejection_coverage.json`,
  diagnostics plus boundary-budget rejection coverage, including fail-closed
  import-preamble drift and annotated-signature coverage, and binding through the Kernel Ingress Proof
  Bundle.
- Source-To-Intent Research Kernel Ingress Conformance Gate at
  `examples/source_to_intent_research_kernel_ingress_conformance_gate.py`,
  with deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_conformance_gate.txt`,
  reusable Source Intent Frontend Conformance coverage for accepted Kernel
  Ingress outputs and rejected Source Intent escape cases, and digest binding
  through Source-To-Intent Research Evidence Gate and Proof Bundle.
- Source-To-Intent Research Kernel Ingress Diagnostics at
  `examples/source_to_intent_research_kernel_ingress_diagnostics.py`, with
  frontend API at
  `src/tuc/frontend/source_to_intent_research_kernel_ingress_diagnostics.py`,
  schema at
  `schemas/source_to_intent_research_kernel_ingress_diagnostics_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_diagnostics_report.json`,
  and digest binding through Source-To-Intent Research Evidence Gate and Proof
  Bundle for accepted/rejected module-shaped source diagnostics, including
  imports-after-kernel and annotated-signature rejection evidence.
- Source-To-Intent Research Kernel Ingress Idiom Alignment at
  `examples/source_to_intent_research_kernel_ingress_idiom_alignment.py`,
  with schema at
  `schemas/source_to_intent_research_kernel_ingress_idiom_alignment_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_idiom_alignment.json`,
  digest binding through Source-To-Intent Research Evidence Gate and Proof
  Bundle, and scope binding from accepted Kernel Ingress outputs to covered
  Triton MVP idioms.
- Source-To-Intent Research Kernel Ingress Proof Bundle at
  `examples/source_to_intent_research_kernel_ingress_proof_bundle.py`, with
  schema at
  `schemas/source_to_intent_research_kernel_ingress_proof_bundle_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_proof_bundle.json`,
  digest binding through Source-To-Intent Research Evidence Gate and global
  Proof Bundle, and one source-free review index for Kernel Ingress E2E,
  runtime-matrix, runtime-coverage-policy, runtime-backend-alignment,
  boundary-budget, rejection-coverage, diagnostics, conformance, and
  idiom-alignment evidence.
- Source-To-Intent Research Kernel Ingress Evidence Gate at
  `examples/source_to_intent_research_kernel_ingress_evidence_gate.py`, with
  deterministic golden evidence at
  `tests/golden/frontend/source_to_intent_research_kernel_ingress_evidence_gate.txt`,
  exact Kernel Ingress Proof Bundle digest binding, runtime-matrix binding,
  runtime-coverage-policy binding, runtime-backend-alignment binding, and
  digest binding through Source-To-Intent Research Evidence Gate and global
  Proof Bundle.
- Source Intent Intake fuzz/property corpus for arbitrary JSON-like values,
  unsupported schema versions, source-text escape attempts, backend hint
  escapes, and unknown tensor references.
- Source Intent Intake end-to-end frontend goldens proving schema-versioned
  plain data can flow through Source Intent IR, metadata intake, HAC-IR,
  runtime planning, and compiler decision reports without source parsing.
- Source Intent Metadata Conversion v0 for execution-free conversion from an
  already constructed `SourceIntentModule` into schema-versioned metadata, with
  frontend, HAC-IR, runtime-plan, and compiler decision-report goldens.
- Baseline benchmark harness that can run with or without CUDA.
- Schema-versioned diagnostic baseline benchmark report contract with explicit
  non-performance-proof markers.
- Diagnostic Planner Overhead Report for compiler/planner phase separation
  with execution timing and break-even claims still blocked.
- Diagnostic Break-Even Workload Size Report for planning-amortization metadata
  without raw timing samples or benchmark artifact loading.
- Diagnostic Leaky Abstraction Report for HAC-IR boundary review with
  hardware-specific performance facts assigned outside HAC-IR.
- Diagnostic Native Baseline Provenance Report for bounded native comparison
  candidate review without native execution or performance claims.
- Diagnostic Native Baseline Comparison Report for bounded comparison metadata
  between baseline and native benchmark artifacts without loading raw outputs.
- Diagnostic Benchmark Artifact Manifest Report for benchmark report inventory
  through bounded IDs, schema versions, digest status, and storage scopes.
- Diagnostic Workload Scope Report for operation-family, shape-profile,
  dtype-policy, problem-size, and correctness-reference boundaries.
- Diagnostic Benchmark Methodology Report for measurement clocks, warmup and
  iteration policy, statistic policy, isolation, outlier handling, and
  reproducibility policy.
- Diagnostic Toolchain Environment Report for versioned runtime, package,
  compiler, driver, container, and OS component inventory without host
  discovery.
- Diagnostic Executable Backend Security Review Report for future executable
  surfaces without approving execution.
- Diagnostic Performance Proof RFC Report for future native performance claim
  proposals, acceptance status, evidence links, security review IDs, and
  digests while keeping native performance claims blocked.
- Diagnostic Performance Claim Threshold Policy Report for future native
  performance threshold metadata while keeping measured performance claims
  blocked.
- Diagnostic Performance Acceptance Criteria Report for future native
  performance pass/fail metadata while keeping measured performance claims
  blocked.
- Performance Proof Boundary documenting that benchmarks are diagnostic until
  native baseline provenance, native baseline comparison, leaky-abstraction
  evidence, planner-overhead evidence, correctness goldens, and executable
  backend security review exist.
- Performance Proof Readiness report with deterministic metadata-complete golden
  evidence for the current Kernel Ingress proof slice, marking accepted
  governance metadata, workload scope, methodology, toolchain environment,
  native-baseline provenance/comparison metadata, leaky-abstraction,
  planner-overhead, break-even, correctness/runtime-plan/compiler-decision
  goldens, benchmark schema/artifact inventory, and executable backend security
  review evidence present while native performance claims remain blocked.
- Performance Proof Interpretation report with deterministic blocked golden
  evidence for the current post-readiness state, linking readiness to a separate
  measurement-interpretation gate.
- First native MLIR design spike.
- HAC-IR v0 dialect contracts for MVP operations and compiler attributes.
- HAC-IR semantic charter for compute intent, compiler facts, planning
  constraints, and forbidden backend details.
- HS-IR v0 contracts for backend assignments, produced layouts, and runtime-transfer summaries.
- Backend API v0.1 authoring guide for external prototype backends.
- Backend author certification checklist and negative-test template.
- Backend conformance fixtures for prototype operation semantics and diagnostics.
- External-style backend author path covering manifest loading, registry
  diagnostics, compiler planning, conformance, and trusted lowering.
- Specialized accelerator manifest path showing `device_sram` and `blocked`
  layout capability self-description without backend code execution.
- Manifest Claim Review for syntactically valid but overreaching specialized
  accelerator claims, including universal operation-family claims and
  noise/calibration claims without explicit error-budget boundaries.
- External backend author path gate that blocks manifests failing Manifest
  Claim Review before they can reach registry diagnostics or lowering.
- Backend Author Readiness report for a single pass/fail external-backend
  onboarding artifact built from bounded review evidence.
- Backend Author Evidence Gate for CI-facing manifest claim review and backend
  author readiness enforcement.
- Deterministic backend conformance report artifacts for reviewable backend
  author evidence.
- Backend capability schema guidance for error-budget, latency, energy,
  calibration, and noise assumptions.
- Capability-schema negative examples for invalid or misleading backend claims.
- Branch protection policy for `main` and expanded required CI smoke surface.
- Release artifact workflow with CycloneDX SBOM, SHA-256 checksums, wheel import
  check, and GitHub provenance/SBOM attestations.
- Release governance policy with SHA-pinned release actions, release-action pin
  tests, and required GitHub/PyPI publishing controls.
- PyPI Trusted Publishing job gated by protected `v*` tags, artifact-build
  success, and the `pypi` environment.
- CODEOWNERS-backed review policy for compiler, runtime, backend, governance,
  and release trust boundaries.
- Explicit backend capability registry for manifest-loaded planning
  data without plugin discovery or backend code execution.
- Pure-data backend support diagnostics that explain accepted and rejected
  operation/backend matches before partitioning.
- Compiler-level decision reports that connect backend support diagnostics to
  final runtime assignments.
- Golden compiler decision-report fixtures for proof and MVP graphs.
- Masterplan-aligned roadmap organized around proof phases instead of a
  compiler-centric implementation timeline.
- Proof-of-abstraction runtime plan is golden-tested independently from the
  full proof report.
- HAC-IR neutrality checklist and executable hardware-leakage guard.
- HAC-IR golden dump fixtures for proof and MVP graphs.
- Second Objective Alpha proof graph with `matmul -> reduction -> elementwise`
  correctness validation.
- Third Objective Alpha proof graph with `matmul -> softmax`, explicit axis
  validation, fallback planning, and correctness validation.
- Deterministic proof-report metadata visible in golden proof reports.
- Reviewer-facing proof artifact checklist and golden-file merge gate.
- Runtime manual override policy for future placement constraints before
  automatic global optimization.
- Schema-versioned runtime manual override v0 with fail-closed negative tests,
  compiler decision-report goldens, and runtime-plan goldens.
- Opt-in runtime candidate score diagnostics with runtime-plan and compiler
  decision-report goldens.
- Softmax operation-family planning contract for future nonlinear proof graphs,
  softmax HAC-IR goldens, runtime-plan goldens, and decision-report goldens.
- Softmax proof graph fixtures with full proof output, HAC-IR dump,
  runtime-plan dump, and compiler decision-report goldens.

### Phase Beta: HAC-IR Contract

Current focus:

- Preserve HAC-IR as the hardware-neutral compute-intent layer.
- Keep vendor-specific assumptions out of HAC-IR semantics.
- Use the HAC-IR semantic charter when deciding whether new facts belong in
  HAC-IR, HS-IR, capabilities, runtime plans, or backend contracts.
- Maintain deterministic HAC-IR proof and MVP dumps.
- Maintain negative tests for hardware-specific leakage into reserved `tuc.*`
  attributes.
- Use the reviewer-facing HAC-IR neutrality checklist for every attribute
  change.
- Use [Softmax operation-family planning](SOFTMAX_OPERATION_PLANNING.md) before
  accepting further softmax-specific HAC-IR changes or decomposition claims.

### Phase Gamma: Capability Framework

Current focus:

- Strengthen backend manifests, registry, diagnostics, and conformance fixtures.
- Keep backend onboarding capability-first and execution-free.
- Use the external-style backend author path as the reference for toy backend
  proposals.
- Store backend conformance evidence as deterministic review artifacts.
- Use compiler decision reports to inspect accepted and rejected backend
  candidates next to final assignments.
- Treat compiler decision-report fixtures as reviewable backend selection
  evidence.
- Keep capability-schema assumptions documented separately from HAC-IR and
  executable backend behavior.
- Keep invalid or misleading capability claims covered by examples and negative
  tests.
- Use Manifest Claim Review before accepting specialized accelerator manifests
  as planning evidence.
- Use Backend Author Readiness before treating an external backend author path
  as complete.
- Keep Backend Author Evidence Gate passing in CI before accepting backend
  onboarding changes.

### Phase Delta: Runtime Planning

Current focus:

- Keep operation placement explainable.
- Golden-test proof runtime plans independently from full proof reports.
- Use compiler decision reports as the bridge between support diagnostics and
  runtime placement.
- Golden-test compiler decision reports for proof and MVP graphs.
- Use [Runtime manual override policy](RUNTIME_OVERRIDE_POLICY.md) as the gate
  before schema-versioned placement overrides, candidate scoring, or automatic
  global optimization.
- Keep `RuntimeOverrideSet` operation-scoped, capability-bounded, inspectable,
  and separate from HAC-IR semantics.
- Use `CandidateScore` diagnostics as the review surface before adding richer
  transfer/noise-aware candidate scoring.
- Keep Runtime Candidate Score Evidence passing before accepting richer scoring
  components or changing candidate score semantics.
- Use Runtime Candidate Scoring Policy before changing comparator order or
  enabling noise, error-budget, calibration, or benchmark score inputs.
- Keep Runtime Candidate Scoring Conformance passing before changing runtime
  candidate comparator behavior.
- Keep Runtime Candidate Scoring Gate passing in CI before accepting richer
  candidate scoring behavior.
- Keep Runtime Planning Explanation and its Runtime Evidence Gate bindings
  passing before accepting new placement reasons, fallback/no-fallback
  semantics, movement-accounting fields, or planning-explanation artifact IDs.
- Use Runtime Buffer Lifetime before adding explicit buffer allocation plans,
  memory-pool behavior, or buffer-reuse claims.
- Use Runtime Allocation Plan before adding memory pools, device allocation,
  aliasing, or real allocator behavior.
- Use Runtime Memory Budget before accepting memory pools, device allocation,
  aliasing, or allocator behavior that can reserve runtime memory.
- Use Runtime Allocation Request Manifest before accepting memory pools, device
  allocation, aliasing, runtime handles, or allocator behavior that can reserve
  runtime memory.
- Use Runtime Allocation Admission before accepting memory pools, device
  allocation, aliasing, runtime handles, or allocator behavior that can admit
  runtime memory requests.
- Use Runtime Allocation Receipt before accepting memory pools, device
  allocation, aliasing, runtime handles, or allocator behavior that can record
  runtime allocation outcomes.
- Keep Runtime Memory Planning Gate and its Runtime Evidence Gate matrix
  binding passing in CI before accepting allocator,
  memory-pool, device-allocation, or aliasing changes.
- Keep Memory Budget reports bound to the Allocation Plan evaluated by the same
  gate invocation before accepting allocator, memory-pool, device-allocation, or
  aliasing changes.
- Keep Allocation Request Manifest reports bound to the Allocation Plan and
  Memory Budget evaluated by the same gate invocation before accepting
  allocator, memory-pool, device-allocation, runtime-handle, or aliasing
  changes.
- Keep Allocation Admission reports bound to the Request Manifest and Memory
  Budget evaluated by the same gate invocation before accepting allocator,
  memory-pool, device-allocation, runtime-handle, or aliasing changes.
- Keep Allocation Receipt reports bound to the Allocation Admission evaluated by
  the same gate invocation before accepting allocator, memory-pool,
  device-allocation, runtime-handle, or aliasing changes.
- Keep Allocation Plan reports bound to the Buffer Lifetime report evaluated by
  the same gate invocation before accepting allocator, memory-pool,
  device-allocation, or aliasing changes.
- Use Runtime HS-IR Plan Alignment before treating backend-specific HS-IR facts
  as practical execution evidence.
- Treat softmax decomposition as runtime/HS-IR planning evidence, not HAC-IR
  semantics.
- Use RFC 0212 before accepting runtime layout conversion behavior, hidden
  backend-local layout transitions, native layout converters, or real
  device-residency claims.

## Next

- Real Triton integration remains the next credibility milestone. The current
  [Triton Integration Readiness](TRITON_INTEGRATION_READINESS.md) report at `examples/triton_integration_readiness.py` is now `ready` as data-only review evidence, [Real Triton Integration Admission Gate](REAL_TRITON_INTEGRATION_ADMISSION_GATE.md) at `examples/real_triton_integration_admission_gate.py` now binds readiness, external package conformance, and [Real Triton Integration Threat Model](REAL_TRITON_INTEGRATION_THREAT_MODEL.md) evidence by digest with schema `schemas/real_triton_integration_admission_gate_report.v0.schema.json`, and [Source Ingestion Quarantine Gate](SOURCE_INGESTION_QUARANTINE_GATE.md) at `examples/source_ingestion_quarantine_gate.py` now establishes the first dedicated surface gate with schema `schemas/source_ingestion_quarantine_gate_report.v0.schema.json`; admission remains blocked until package import, plugin discovery, Triton JIT, device access, generated artifacts, and native backend execution each have dedicated gates, and source ingestion remains quarantine-only.
- Future Triton idiom coverage should enter through the schema-versioned
  metadata intake contract and
  [Triton Idiom Coverage Report](TRITON_IDIOM_COVERAGE_REPORT.md) before any
  source parser or `@triton.jit` handling is accepted.
- General source parser work must satisfy
  [Triton Source Threat Model](TRITON_SOURCE_THREAT_MODEL.md) before it can
  produce metadata, HAC-IR, runtime-plan, or decision-report artifacts.
- Source preflight is allowed only as a diagnostic boundary; future canonical
  source-intent IR must remain disconnected from lowering until fuzzing and
  golden review evidence exist.
- Source preflight fuzzing is now the baseline seed set; Source Intent IR v0
  can be built from schema-versioned plain data and can convert to metadata
  only through separate reviewed adapters. The explicit research parser may
  emit `source_intent.v0` plain data for its narrow accepted subset, but any
  broader source-text-to-intent work must add its own corpus, source-intent
  goldens, deterministic diagnostics, and security review before expansion.
- External frontend proposals should provide a Source Intent Frontend
  Conformance report matching the report schema and pass Source Intent Frontend
  Conformance Gate before maintainers consider any source-text parser or
  frontend package integration.
- Default source-to-intent parser intake remains blocked by
  [Source-To-Intent Parser Gate](SOURCE_TO_INTENT_PARSER_GATE.md); the accepted
  research parser is explicit-only and must not become a compiler shortcut.
- Add future parser syntax only after each new Source Intent semantic attribute
  has its own intake, metadata-conversion, conformance, and golden evidence.
- Extend Source-To-Intent Research Diagnostics with source-free accepted and
  rejected cases before any parser syntax expands beyond the current research
  subset.
- Future parser proposals must pass
  [Source-To-Intent Readiness Report](SOURCE_TO_INTENT_READINESS.md) before
  source text can influence compiler artifacts.
- Future softmax decomposition only after runtime/HS-IR planning evidence,
  capability diagnostics, and proof goldens stay inspectable.
- Candidate scoring only after transfer/noise-aware models are stable and its
  decisions can be explained next to manual override effects.
- Native performance claims remain blocked until a separate performance proof
  proposal interprets accepted measurement artifacts under the
  [Performance Proof Boundary](PERFORMANCE_PROOF_BOUNDARY.md); a passing
  [Performance Proof Readiness Report](PERFORMANCE_PROOF_READINESS.md) and
  [Performance Proof Interpretation Report](PERFORMANCE_PROOF_INTERPRETATION.md)
  are necessary metadata, not the proof itself.
- Noise/error-budget score components only after those models are documented
  outside HAC-IR semantics and covered by goldens.
- Maintainer teams or organization-backed owner groups before broad external
  contribution.
- Backend Plugin Lifecycle Policy now supplies the plugin lifecycle RFC and
  blocking policy. Backend Plugin Sandbox Model supplies the accepted
  data-only sandbox model, Backend Plugin Artifact Provenance supplies accepted
  digest-bound provenance, and Backend Plugin Resource Budget supplies accepted
  static budget evidence, and Backend Plugin Fuzz Negative Tests supplies
  accepted deterministic rejection evidence, and Backend Plugin Maintainer
  Approval supplies accepted proposal-gate evidence. Executable backend
  discovery, artifact execution, or native plugin ABI still require a separate
  implementation RFC and policy change.
- Runtime Layout Conversion Evidence is now graph-scoped required Runtime
  Evidence Matrix and Runtime Evidence Gate evidence for
  `runtime_mixed_backend_equivalence`, backed by Gate Readiness, Digest
  Binding, and Gate Promotion Policy artifacts.

## Runtime Allocation Reconciliation

- Runtime Allocation Reconciliation at `examples/runtime_allocation_reconciliation.py`, schema at `schemas/runtime_allocation_reconciliation_report.v0.schema.json`, and golden at `tests/golden/runtime_allocation_reconciliation/current_report.json` now reconcile Admission and Receipt before any allocator handle or memory address surface exists.
