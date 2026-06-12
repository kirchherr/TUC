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
- Runtime Memory Planning Gate v0 with deterministic golden evidence at
  `tests/golden/runtime_memory_planning_gate/current_gate.txt` and CI coverage
  in the `python` workflow job, now verifying Allocation Plan binding to Buffer
  Lifetime, Memory Budget binding to Allocation Plan, and Allocation Request
  Manifest binding to Allocation Plan and Memory Budget in the same gate
  invocation.
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
  tensor-store, input-manifest, output-manifest, and reference-correctness
  evidence by metadata digest without raw tensor values.
- Runtime Execution Evidence Bundle v0 with schema at
  `schemas/runtime_execution_evidence_bundle_report.v0.schema.json`,
  deterministic golden evidence at
  `tests/golden/runtime_execution_evidence_bundle/proof_of_execution.json`,
  packaging tensor-store, input-manifest, output-manifest,
  reference-correctness, and execution-receipt reports into one metadata-only
  review artifact.
- Runtime Execution Evidence Bundle Binding in Runtime Evidence Gate, rejecting
  stale or forged bundles whose embedded graph names, contracts, metadata
  digests, item counts, pass status, or raw-value policy do not match the
  evidence reports evaluated by the same gate invocation, with the decision
  captured in
  `rfcs/0130-runtime-evidence-gate-execution-bundle-binding.md`.
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
  runtime evidence digests and operation trace metadata without tensor values.
- Runtime Execution Evidence Bundle at
  `examples/runtime_execution_evidence_bundle.py`, with golden evidence at
  `tests/golden/runtime_execution_evidence_bundle/proof_of_execution.json`,
  embedding the receipt and evidence reports as one metadata-only review
  package.
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
  Equivalence, Runtime Vector Backend Equivalence, Runtime Mixed Backend
  Equivalence, Runtime Tensor Store Evidence, Runtime Input Manifest, Runtime
  Output Manifest, Runtime Output Contract, Runtime Public Output Bundle,
  Runtime Reference Correctness, Runtime Execution Receipt, Runtime Execution
  Evidence Bundle, and Source Intent Runtime Returns, with binding checks for
  the backend-equivalence fixture and the `source_intent_return_mlp` frontend
  fixture.
- Runtime Candidate Score Evidence at
  `examples/runtime_candidate_score_evidence.py`, with golden evidence at
  `tests/golden/runtime_candidate_score_evidence/profiled_candidate_score_report.json`.
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
- Runtime Memory Planning Gate at `examples/runtime_memory_planning_gate.py`,
  with golden evidence at
  `tests/golden/runtime_memory_planning_gate/current_gate.txt`, rejecting stale
  Allocation Plan evidence whose source Buffer Lifetime digest does not match
  stale Memory Budget evidence whose source Allocation Plan digest does not
  match, and stale Allocation Request Manifest evidence whose source Allocation
  Plan or Memory Budget binding does not match.
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
- Performance Proof Readiness report with deterministic blocked golden evidence
  for future native performance proposals.
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
- Use Runtime Buffer Lifetime before adding explicit buffer allocation plans,
  memory-pool behavior, or buffer-reuse claims.
- Use Runtime Allocation Plan before adding memory pools, device allocation,
  aliasing, or real allocator behavior.
- Use Runtime Memory Budget before accepting memory pools, device allocation,
  aliasing, or allocator behavior that can reserve runtime memory.
- Use Runtime Allocation Request Manifest before accepting memory pools, device
  allocation, aliasing, runtime handles, or allocator behavior that can reserve
  runtime memory.
- Keep Runtime Memory Planning Gate passing in CI before accepting allocator,
  memory-pool, device-allocation, or aliasing changes.
- Keep Memory Budget reports bound to the Allocation Plan evaluated by the same
  gate invocation before accepting allocator, memory-pool, device-allocation, or
  aliasing changes.
- Keep Allocation Request Manifest reports bound to the Allocation Plan and
  Memory Budget evaluated by the same gate invocation before accepting
  allocator, memory-pool, device-allocation, runtime-handle, or aliasing
  changes.
- Keep Allocation Plan reports bound to the Buffer Lifetime report evaluated by
  the same gate invocation before accepting allocator, memory-pool,
  device-allocation, or aliasing changes.
- Use Runtime HS-IR Plan Alignment before treating backend-specific HS-IR facts
  as practical execution evidence.
- Treat softmax decomposition as runtime/HS-IR planning evidence, not HAC-IR
  semantics.

## Next

- Real Triton integration as a credibility milestone after the abstraction proof
  remains stable.
- Future Triton idiom coverage should enter through the schema-versioned
  metadata intake contract and
  [Triton Idiom Coverage Report](TRITON_IDIOM_COVERAGE_REPORT.md) before any
  source parser or `@triton.jit` handling is accepted.
- Source parser work must satisfy
  [Triton Source Threat Model](TRITON_SOURCE_THREAT_MODEL.md) before it can
  produce metadata, HAC-IR, runtime-plan, or decision-report artifacts.
- Source preflight is allowed only as a diagnostic boundary; future canonical
  source-intent IR must remain disconnected from lowering until fuzzing and
  golden review evidence exist.
- Source preflight fuzzing is now the baseline seed set; Source Intent IR v0
  can be built from schema-versioned plain data and can convert to metadata
  only through separate reviewed adapters. Future source-text-to-intent work
  must add its own corpus, source-intent goldens, deterministic diagnostics,
  and security review before any source connection.
- External frontend proposals should provide a Source Intent Frontend
  Conformance report matching the report schema and pass Source Intent Frontend
  Conformance Gate before maintainers consider any source-text parser or
  frontend package integration.
- Source-to-intent parser work remains blocked until
  [Source-To-Intent Parser Gate](SOURCE_TO_INTENT_PARSER_GATE.md) is satisfied
  by a dedicated parser implementation RFC and executable evidence.
- Future parser proposals must pass
  [Source-To-Intent Readiness Report](SOURCE_TO_INTENT_READINESS.md) before
  source text can influence compiler artifacts.
- Future softmax decomposition only after runtime/HS-IR planning evidence,
  capability diagnostics, and proof goldens stay inspectable.
- Candidate scoring only after transfer/noise-aware models are stable and its
  decisions can be explained next to manual override effects.
- Native performance claims remain blocked until
  [Performance Proof Boundary](PERFORMANCE_PROOF_BOUNDARY.md) is satisfied and
  [Performance Proof RFC Report](PERFORMANCE_PROOF_RFC_REPORT.md),
  [Performance Claim Threshold Policy Report](PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT.md),
  [Performance Acceptance Criteria Report](PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT.md),
  and
  [Performance Proof Readiness Report](PERFORMANCE_PROOF_READINESS.md) pass.
- Noise/error-budget score components only after those models are documented
  outside HAC-IR semantics and covered by goldens.
- Maintainer teams or organization-backed owner groups before broad external
  contribution.
- Plugin lifecycle RFC and sandboxing model before any executable backend
  discovery, artifact execution, or native plugin ABI.
