# TUC

TUC is **The Universal Compute**: an early-stage open-source prototype exploring
whether compute intent can move through a hardware-independent interface into
capability-driven runtime planning and controlled execution.

TUC is not trying to become just another compiler. It is testing whether
software can describe intent, hardware can describe capabilities, and the
translation layer between them can stay inspectable, secure, and portable.

- Strategic north star: [TUC Master Plan](TUC_MASTER_PLAN.md)
- Operational status: [Roadmap Status](docs/ROADMAP_STATUS.md)
- First research proof path:
  [Research Onboarding Slice](docs/RESEARCH_ONBOARDING_SLICE.md)
- External feedback triage:
  [2026-06-22 Review Response](docs/EXTERNAL_REVIEW_TRIAGE_2026_06_22.md)

## Core Claims

Current narrow claim:

> Compute intent can be represented independently of hardware, planned across
> backend capabilities, executed by trusted prototype backends, and checked
> against deterministic reference semantics without changing mathematical
> intent.

TUC protects three boundaries:

- **HAC-IR:** hardware-neutral compute intent.
- **Capabilities:** backend self-description as bounded data.
- **Runtime planning:** explainable placement, movement, memory, and execution
  evidence.

Current high-level research claim artifact:

```bash
python examples/source_to_intent_research_capability_claim.py
python examples/source_to_intent_research_capability_claim_gate.py
```

## Current Proofs

Objective Alpha is the current proof shape:

```text
Graph -> HAC-IR -> Runtime Plan -> Backend A + Backend B -> Correct Result
```

Run the proof family:

```bash
python examples/proof_of_abstraction.py
python examples/proof_of_reduction.py
python examples/proof_of_softmax.py
python examples/proof_of_execution.py
python examples/proof_of_systolic_execution.py
```

Review the proof inventory:

```bash
python examples/runtime_evidence_matrix.py
python examples/runtime_evidence_gate.py
```

Review the first-run onboarding evidence:

```bash
python examples/research_onboarding_evidence.py
```

See [Research Onboarding Evidence](docs/RESEARCH_ONBOARDING_EVIDENCE.md).

Review the Objective Alpha public proof bundle:

```bash
python examples/objective_alpha_public_proof_bundle.py
```

See [Objective Alpha Public Proof Bundle](docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE.md).
It directly exposes Proof Of Backend Equivalence plus output-closure,
transfer-boundary trace index/replay/binding, layout-transition trace
index/replay/binding, allocation-reconciliation, Source-To-Intent Research
Proof Bundle, and Kernel Ingress Evidence Gate evidence as digest-only public
entries, with an
[Objective Alpha Public Proof Bundle Gate](docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md)
to keep the top-level review surface fixed and claim-safe. The follow-on
[Objective Alpha Evidence Extension Policy](docs/OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY.md)
keeps future evidence growth out of the fixed 16-entry public bundle unless a
new RFC or successor evidence catalog deliberately opens that path. The
[Objective Alpha Public Evidence Catalog](docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md)
now provides that separate digest-only growth surface, with an
[Objective Alpha Public Evidence Catalog Admission Gate](docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md)
checking append-only, RFC-bound, digest-only admission rules. A typed catalog
entry admission pattern now derives the catalog's expected IDs, entry points,
artifact kinds, extension tiers, digest sources, and raw-output policies from
reviewed data-only specs. The catalog now also emits required extension-tier
coverage evidence for `governance`, `runtime_proof`,
`frontend_runtime_proof`, and `claim_boundary`, so reviewers can see that
Objective Alpha covers the current governance, backend-equivalence,
source-ingress, and claim-boundary proof roles. Its first non-governance
catalog entry binds the Runtime Backend Equivalence Portfolio as
`runtime_proof` evidence, its first `frontend_runtime_proof` entry binds the
Source-To-Intent Kernel Ingress Proof Bundle, and its `claim_boundary` entry
binds the Source-To-Intent Research Capability Claim Gate without expanding the
fixed public bundle.

## Runtime Execution

Runtime Executor v0 runs already-compiled graphs through a fixed trusted
in-process executor registry. It is intentionally not a plugin system and does
not authorize external executable backend artifacts.

Current runtime surfaces:

- Runtime Execution Readiness before kernels run.
- Runtime Tensor Store v0 with internal read-only `RuntimeValueRecord` objects.
- Runtime Tensor Store Evidence v0 without serialized tensor values.
- Runtime Input Manifest v0 for graph external inputs without serialized tensor
  values.
- Runtime Output Manifest v0 for terminal graph outputs without serialized
  tensor values.
- Runtime Output Contract v0 for explicit public output aliases without
  serialized tensor values.
- Runtime Public Output Bundle v0 for resolving public aliases to read-only
  runtime values while keeping review evidence metadata-only.
- Source Intent Runtime Returns v0 for proving frontend public return intent
  resolves through Runtime Output Contract and Runtime Public Output Bundle.
- Runtime Reference Correctness v0 for output/reference comparison without
  serialized tensor values.
- Runtime Execution Receipt v0 linking runtime evidence reports, public output
  contracts, and public output bundles by metadata digest without serialized
  tensor values.
- Runtime Execution Evidence Bundle v0 packaging one coherent metadata-only
  execution evidence set, including the public output boundary, for review.
- Runtime Execution Output Closure v0 auditing that Receipt and Evidence Bundle
  bind the same public Output Contract and Public Output Bundle across
  proof-of-execution, multi-output, and softmax fixtures.
- Runtime Evidence Replay Verifier v0 replay-checking serialized Runtime
  Execution Evidence Bundle and Runtime Execution Output Closure reports by
  metadata digest without re-running source, JIT, plugins, devices, or backend
  artifacts.
- Runtime Backend Equivalence v0 comparing `reference-cpu` against
  `systolic-sim`, `vector-sim`, and mixed `systolic-sim` plus `vector-sim`
  placements without serialized tensor values, with all proof slices bound into
  the Runtime Evidence Gate.
- Proof Of Backend Equivalence v0 promoting the mixed `reference-cpu` versus
  `systolic-sim + vector-sim` placement comparison into one canonical
  metadata-only proof entrypoint.
- Mixed Runtime Tensor Store Evidence v0 proving the accepted
  `systolic-sim -> vector-sim` plan produces read-only Runtime Value Records
  with placement metadata and without serialized tensor values.
- Runtime Backend Equivalence Portfolio v0 aggregating the systolic, vector,
  and mixed accelerator equivalence slices into one backend-diversity evidence
  artifact inventoried by Runtime Evidence Matrix and bound by the Runtime
  Evidence Gate.
- Runtime Backend Equivalence Portfolio Policy v0 declaring the accepted
  portfolio slice membership and backend-family coverage as data-only evidence.
- Runtime HS-IR Plan Alignment v0 binding HS-IR backend/layout decisions to
  the accepted `PartitionPlan` and observed `RuntimeExecutionTrace`, now
  inventoried by Runtime Evidence Matrix and required by Runtime Evidence Gate
  for the mixed accelerator proof slice.
- Runtime Buffer Lifetime, Allocation Plan, Memory Budget, Allocation Request
  Manifest, Allocation Admission, Allocation Receipt, and Memory Planning Gate,
  now inventoried by Runtime Evidence Matrix and required by Runtime Evidence
  Gate through exact artifact IDs.
- Runtime Candidate Score Evidence, Policy, Conformance, and Scoring Gate.
- Runtime Planning Explanation v0 for accepted `PartitionPlan` backend
  sequence, fallback/no-fallback placement, candidate-score visibility, and
  movement accounting, now bound into Runtime Evidence Matrix and Runtime
  Evidence Gate for the systolic and mixed backend-equivalence slices.
- Runtime Transfer Evidence v0 for planned cross-domain runtime transfers as
  data-only review evidence with deterministic planning-cost estimates and no
  device-residency or native-performance claim.
- Runtime Transfer Trace Index v0 binds planned cross-domain transfers to
  concrete producer and consumer Runtime Execution Trace steps without
  materializing a transfer step, now required by Runtime Evidence Matrix and
  Runtime Evidence Gate for the systolic backend-equivalence proof slice.
- Runtime Transfer Trace Replay Verifier v0 replay-checking serialized Transfer
  Evidence and Transfer Trace Index reports by metadata digest without rerunning
  runtime execution or materializing transfer steps, now required by Runtime
  Evidence Matrix and Runtime Evidence Gate for the systolic proof slice.
- Runtime Backend Equivalence Transfer Binding v0 binding systolic backend
  equivalence to verified transfer trace replay by metadata digest, proving the
  same graph carries both terminal semantics and transfer-boundary evidence;
  now required by Runtime Evidence Matrix and Runtime Evidence Gate.
- Runtime Layout Conversion Trace Index v0 binds planned `blocked -> row_major`
  transition evidence to concrete producer and consumer Runtime Execution Trace
  steps without materializing a converter step, now required by Runtime Evidence
  Matrix and Runtime Evidence Gate for the mixed backend-equivalence proof slice.
- Runtime Layout Conversion Trace Replay Verifier v0 replay-checking serialized
  Layout Conversion Evidence and Trace Index reports by metadata digest without
  re-running runtime execution or materializing converter steps.
- Runtime Backend Equivalence Layout Binding v0 binding mixed backend
  equivalence to verified layout trace replay by metadata digest, proving the
  same graph carries both terminal semantics and layout-transition evidence.
- Operation/value contract checks for shapes, `float64`, finite values, and
  MVP operation semantics.

CI-facing runtime evidence entry points:

```text
examples/runtime_evidence_gate.py
examples/runtime_tensor_store_evidence.py
examples/runtime_systolic_tensor_store_evidence.py
examples/runtime_mixed_tensor_store_evidence.py
examples/runtime_input_manifest.py
examples/runtime_execution_receipt.py
examples/runtime_execution_evidence_bundle.py
examples/runtime_execution_output_closure.py
examples/runtime_evidence_replay_verifier.py
examples/runtime_multi_output_execution_output_closure.py
examples/runtime_softmax_execution_output_closure.py
examples/runtime_backend_equivalence.py
examples/runtime_backend_equivalence_portfolio.py
examples/runtime_backend_equivalence_portfolio_policy.py
examples/runtime_vector_backend_equivalence.py
examples/runtime_mixed_backend_equivalence.py
examples/proof_of_backend_equivalence.py
examples/runtime_hs_ir_plan_alignment.py
examples/runtime_planning_explanation.py
examples/runtime_mixed_planning_explanation.py
examples/runtime_transfer_evidence.py
examples/runtime_transfer_trace_index.py
examples/runtime_transfer_trace_replay_verifier.py
examples/runtime_backend_equivalence_transfer_binding.py
examples/runtime_output_contract.py
examples/runtime_public_output_bundle.py
examples/source_intent_runtime_returns.py
examples/runtime_reference_correctness.py
examples/runtime_candidate_scoring_gate.py
examples/runtime_allocation_request_manifest.py
examples/runtime_allocation_admission.py
examples/runtime_allocation_receipt.py
examples/runtime_allocation_reconciliation.py
examples/runtime_memory_planning_gate.py
examples/runtime_layout_conversion_trace_index.py
examples/runtime_layout_conversion_trace_replay_verifier.py
examples/runtime_backend_equivalence_layout_binding.py
```

Key docs:

- [Runtime Executor](docs/RUNTIME_EXECUTOR.md)
- [Runtime Evidence Flow](docs/RUNTIME_EVIDENCE_FLOW.md)
- [Objective Alpha Public Proof Bundle Gate](docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md)
- [Objective Alpha Evidence Extension Policy](docs/OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY.md)
- [Objective Alpha Public Evidence Catalog](docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md)
- [Objective Alpha Public Evidence Catalog Admission Gate](docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md)
- [Runtime Tensor Store](docs/RUNTIME_TENSOR_STORE.md)
- [Runtime Tensor Store Evidence](docs/RUNTIME_TENSOR_STORE_EVIDENCE.md)
- [Runtime Input Manifest](docs/RUNTIME_INPUT_MANIFEST.md)
- [Runtime Output Manifest](docs/RUNTIME_OUTPUT_MANIFEST.md)
- [Runtime Execution Receipt](docs/RUNTIME_EXECUTION_RECEIPT.md)
- [Runtime Execution Evidence Bundle](docs/RUNTIME_EXECUTION_EVIDENCE_BUNDLE.md)
- [Runtime Execution Output Closure](docs/RUNTIME_EXECUTION_OUTPUT_CLOSURE.md)
- [Runtime Evidence Replay Verifier](docs/RUNTIME_EVIDENCE_REPLAY_VERIFIER.md)
- [Runtime Backend Equivalence](docs/RUNTIME_BACKEND_EQUIVALENCE.md)
- [Proof Of Backend Equivalence](docs/PROOF_OF_BACKEND_EQUIVALENCE.md)
- [Runtime Backend Equivalence Portfolio](docs/RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO.md)
- [Runtime Evidence Gate Matrix Coverage](docs/RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE.md)
- [Runtime HS-IR Plan Alignment](docs/RUNTIME_HS_IR_PLAN_ALIGNMENT.md)
- [Runtime Planning Explanation](docs/RUNTIME_PLANNING_EXPLANATION.md)
- [Runtime Transfer Evidence](docs/RUNTIME_TRANSFER_EVIDENCE.md)
- [Runtime Transfer Trace Index](docs/RUNTIME_TRANSFER_TRACE_INDEX.md)
- [Runtime Transfer Trace Replay Verifier](docs/RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER.md)
- [Runtime Backend Equivalence Transfer Binding](docs/RUNTIME_BACKEND_EQUIVALENCE_TRANSFER_BINDING.md)
- [Runtime Layout Conversion Evidence](docs/RUNTIME_LAYOUT_CONVERSION_EVIDENCE.md)
- [Runtime Layout Conversion Trace Index](docs/RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX.md)
- [Runtime Layout Conversion Trace Replay Verifier](docs/RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER.md)
- [Runtime Backend Equivalence Layout Binding](docs/RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING.md)
- [Runtime Output Contract](docs/RUNTIME_OUTPUT_CONTRACT.md)
- [Runtime Public Output Bundle](docs/RUNTIME_PUBLIC_OUTPUT_BUNDLE.md)
- [Runtime Reference Correctness](docs/RUNTIME_REFERENCE_CORRECTNESS.md)
- [Runtime Allocation Request Manifest](docs/RUNTIME_ALLOCATION_REQUEST_MANIFEST.md)
- [Runtime Allocation Admission](docs/RUNTIME_ALLOCATION_ADMISSION.md)
- [Runtime Allocation Receipt](docs/RUNTIME_ALLOCATION_RECEIPT.md)
- [Runtime Allocation Reconciliation](docs/RUNTIME_ALLOCATION_RECONCILIATION.md)
- [Runtime Memory Planning Gate](docs/RUNTIME_MEMORY_PLANNING_GATE.md)
- [Runtime Candidate Scoring Gate](docs/RUNTIME_CANDIDATE_SCORING_GATE.md)
- [Runtime override policy](docs/RUNTIME_OVERRIDE_POLICY.md)

Runtime schemas:

```text
schemas/runtime_input_manifest_report.v0.schema.json
schemas/runtime_execution_receipt_report.v0.schema.json
schemas/runtime_execution_evidence_bundle_report.v0.schema.json
schemas/runtime_execution_output_closure_report.v0.schema.json
schemas/runtime_evidence_replay_verifier_report.v0.schema.json
schemas/runtime_backend_equivalence_report.v0.schema.json
schemas/runtime_backend_equivalence_portfolio_report.v0.schema.json
schemas/runtime_backend_equivalence_portfolio_policy_report.v0.schema.json
schemas/runtime_evidence_gate_matrix_coverage_report.v0.schema.json
schemas/runtime_hs_ir_plan_alignment_report.v0.schema.json
schemas/runtime_planning_explanation_report.v0.schema.json
schemas/runtime_transfer_evidence_report.v0.schema.json
schemas/runtime_transfer_trace_index_report.v0.schema.json
schemas/runtime_transfer_trace_replay_verifier_report.v0.schema.json
schemas/runtime_backend_equivalence_transfer_binding_report.v0.schema.json
schemas/runtime_layout_conversion_trace_index_report.v0.schema.json
schemas/runtime_layout_conversion_trace_replay_verifier_report.v0.schema.json
schemas/runtime_backend_equivalence_layout_binding_report.v0.schema.json
schemas/runtime_output_contract_report.v0.schema.json
schemas/runtime_public_output_bundle_report.v0.schema.json
schemas/source_intent_runtime_returns_report.v0.schema.json
schemas/runtime_allocation_request_manifest_report.v0.schema.json
schemas/runtime_allocation_admission_report.v0.schema.json
schemas/runtime_allocation_receipt_report.v0.schema.json
schemas/runtime_allocation_reconciliation_report.v0.schema.json
```

## Frontend Intake

TUC does not accept Triton/Python source as a default compiler input path and
does not execute source code.

TUC's frontend goal is a research proof of a safe source-intent boundary, not a
claim that this project replaces CUDA, ROCm, XLA, TVM, or production vendor
compiler stacks.

Accepted intake path:

```text
schema-versioned metadata or Source Intent data
    -> intake report
    -> ComputeGraph
    -> HAC-IR
```

Current frontend surfaces:

- Triton-like metadata adapter.
- Execution-free Triton Source Preflight.
- Explicit Source-To-Intent Research Parser v0 for a tiny caller-provided
  Triton-like source subset that emits only validated `source_intent.v0` plain
  data.
- Source-To-Intent Research Parser Conformance Gate proving the first parser
  output slice passes the reusable Source Intent Frontend Conformance path.
- Source-To-Intent Research Diagnostics proving accepted parser cases and
  whitelisted rejected cases, including annotated signatures, remain
  deterministic, source-free, and bounded.
- Source-To-Intent Research Preflight Bridge proving accepted and rejected
  parser diagnostics, including annotation rejection, remain gated by
  execution-free Triton Source Preflight.
- Source-To-Intent Research Evidence Gate binding research readiness,
  conformance, and diagnostics by digest.
- Source-To-Intent Research Execution Bridge proving accepted parser output can
  re-enter Source Intent Intake and reach controlled Runtime Executor evidence.
- Source-To-Intent Research Idiom Alignment proving accepted parser slices stay
  within the already covered Triton-like MVP idiom scope.
- Source-To-Intent Research Proof Bundle providing one digest-only review entry
  for the current safe source-to-runtime research slice.
- Source-To-Intent Research Capability Claim summarizing the currently
  supported bounded Universal Compute research slice and explicitly blocking
  production parser, native performance, hardware certification, arbitrary
  backend execution, and vendor compiler replacement claims.
- Source-To-Intent Research Capability Claim Gate binding that high-level
  claim into CI as source-free text evidence, including the exact thirteen
  evidence IDs that support the bounded research claim.
- Source-To-Intent Research Source Runtime Smoke proving accepted source
  buffers can run end-to-end through the controlled research path.
- Source-To-Intent Research Kernel Ingress proving realistic Triton
  module-shaped source buffers with a fixed import prelude and one plain
  `@triton.jit` kernel can be validated, extracted, and executed through the
  same controlled research path, currently across
  `matmul_elementwise`, `softmax_reduction`, `matmul_reduction`,
  `softmax_elementwise`, and the combined `mvp_pipeline` slice.
- Source-To-Intent Research Kernel Ingress Runtime Matrix making accepted
  module-shaped runtime coverage explicit by backend sequence, terminal output,
  trace-step count, and runtime evidence digest.
- Source-To-Intent Research Kernel Ingress Backend Equivalence proving accepted
  module-shaped Source Intent preserves terminal public outputs under a
  neutral `reference-cpu` baseline and capability-selected trusted simulator
  placements.
- Source-To-Intent Research Kernel Ingress Runtime Coverage Policy requiring
  current accepted runtime cases, backend sequences, terminal outputs, and
  runtime digest fields before Kernel Ingress proof evidence can pass.
- Source-To-Intent Research Kernel Ingress Runtime Backend Alignment binding
  accepted backend sequences to trusted Runtime Executor conformance for
  `linear-sim` and `vector-sim`.
- Source-To-Intent Research Kernel Ingress Boundary Budget proving accepted
  module-shaped inputs stay within resource limits and budget overflow rejects
  before extraction or lowering.
- Source-To-Intent Research Kernel Ingress Rejection Coverage proving current
  diagnostics and budget rejection surfaces are source-free and complete,
  including import-preamble drift and annotated-signature rejection.
- Source-To-Intent Research Kernel Ingress Conformance Gate proving Kernel
  Ingress outputs pass the reusable Source Intent Frontend Conformance path.
- Source-To-Intent Research Kernel Ingress Diagnostics proving accepted and
  rejected module-shaped source cases, including annotated signatures, stay
  source-free, bounded, and fail-closed.
- Source-To-Intent Research Kernel Ingress Idiom Alignment proving accepted
  module-shaped source outputs remain inside covered Triton MVP idioms.
- Source-To-Intent Research Kernel Ingress Proof Bundle giving reviewers one
  digest-only entry point for the Kernel Ingress research slice.
- Source-To-Intent Research Kernel Ingress Evidence Gate binding the focused
  Kernel Ingress proof slice as CI-facing source-free evidence.
- Triton Integration Readiness defining the next Real Triton Integration
  milestone as data-only review evidence with direct source ingestion and JIT
  execution still blocked. Schema: `schemas/triton_integration_readiness_report.v0.schema.json`; entry point: `examples/triton_integration_readiness.py`.
- Real Triton Integration Admission Gate binding readiness, external frontend
  conformance, and threat-model evidence by digest while admission stays
  blocked until source ingestion, package import, plugin discovery, JIT, device
  access, generated artifacts, and native backend execution each have dedicated
  gates. Schema: `schemas/real_triton_integration_admission_gate_report.v0.schema.json`; entry point: `examples/real_triton_integration_admission_gate.py`; docs: `docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md`, `docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md`.
- Source Ingestion Quarantine Gate establishing the first dedicated Real Triton
  Integration surface gate for `direct_source_ingestion`, with source buffers
  treated as untrusted, preflight-only, digest-only evidence and no
  source-to-ComputeGraph/HAC-IR/runtime-plan path admitted. Schema: `schemas/source_ingestion_quarantine_gate_report.v0.schema.json`; entry point: `examples/source_ingestion_quarantine_gate.py`; doc: `docs/SOURCE_INGESTION_QUARANTINE_GATE.md`.
- Package Import Sandbox Gate establishing the next dedicated Real Triton
  Integration surface gate for `frontend_package_import`, with external package
  integration kept manifest/fixture-only and no Python import, package code
  execution, entrypoint discovery, network, filesystem, environment,
  subprocess, or dynamic-library surface admitted. Schema: `schemas/package_import_sandbox_gate_report.v0.schema.json`; entry point: `examples/package_import_sandbox_gate.py`; doc: `docs/PACKAGE_IMPORT_SANDBOX_GATE.md`.
- Plugin Discovery Allowlist Gate establishing the third dedicated Real Triton
  Integration surface gate for `plugin_discovery`, with plugin discovery,
  entrypoint discovery, registry scans, filesystem scans, plugin code
  execution, frontend package import, Python import, network, subprocess,
  dynamic-library, and device surfaces still blocked. Schema: `schemas/plugin_discovery_allowlist_gate_report.v0.schema.json`; entry point: `examples/plugin_discovery_allowlist_gate.py`; doc: `docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md`.
- Source-To-Intent Next Syntax Slice proving branched dataflow, fanout reuse,
  all MVP operation families, and multiple public returns through source-free
  semantic mapping evidence. Schema: `schemas/source_to_intent_next_syntax_report.v0.schema.json`; entry point: `examples/source_to_intent_next_syntax_slice.py`; doc: `docs/SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE.md`.
- External Frontend Package Conformance proving an external frontend can be
  reviewed as a data-only Source Intent package manifest plus digest-only
  fixtures without package import, plugin discovery, source ingestion, or JIT.
  Schema: `schemas/external_frontend_package_conformance_report.v0.schema.json`; entry point: `examples/external_frontend_package_conformance.py`; doc: `docs/EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE.md`.
- Source Intent IR, schema, intake, return semantics, conformance, and metadata
  conversion.
- Source Intent Axis Attributes for neutral `softmax` and `reduction` axis
  semantics.
- Source Intent Frontend Conformance Gate for CI-facing external frontend
  plain-data and public-return evidence.
- Source Intent Runtime Returns evidence connecting explicit frontend returns
  to runtime public outputs after trusted execution.
- Source-To-Intent Parser Block Gate proving the default source parser path
  remains intentionally closed.
- Source-To-Intent Corpus Evidence defining accepted and rejected source-buffer
  fixtures for the first narrow parser proof without emitting Source Intent IR.
- Source-To-Intent Property Corpus evidence defining fuzz/property obligations
  for the first narrow parser proof without running parser logic.
- Source-To-Intent Parser Report v0 defining a proposal-only parser report
  golden with `parser_enabled = false`.
- Source-To-Intent Research Readiness evidence showing current progress toward
  the first narrow parser proof while the default parser path remains closed.
- The default Source-to-Intent parser path remains blocked; the explicit
  research parser is not wired into compiler intake and does not bypass Source
  Intent Intake.

CI-facing frontend evidence entry points:

```text
examples/source_intent_frontend_conformance_gate.py
examples/source_intent_frontend_conformance.py
examples/source_intent_runtime_returns.py
examples/source_to_intent_corpus.py
examples/source_to_intent_property_corpus.py
examples/source_to_intent_parser_report.py
examples/source_to_intent_research_parser.py
examples/source_to_intent_research_parser_conformance_gate.py
examples/source_to_intent_research_diagnostics.py
examples/source_to_intent_research_preflight_bridge.py
examples/source_to_intent_research_execution_bridge.py
examples/source_to_intent_research_idiom_alignment.py
examples/source_to_intent_research_evidence_gate.py
examples/source_to_intent_research_proof_bundle.py
examples/source_to_intent_research_capability_claim.py
examples/source_to_intent_research_capability_claim_gate.py
examples/source_to_intent_research_kernel_ingress.py
examples/source_to_intent_research_kernel_ingress_runtime_matrix.py
examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py
examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py
examples/source_to_intent_research_kernel_ingress_runtime_output_closure_index.py
examples/source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.py
examples/source_to_intent_research_kernel_ingress_backend_equivalence.py
examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py
examples/source_to_intent_research_kernel_ingress_workload_scope.py
examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py
examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py
examples/source_to_intent_research_kernel_ingress_boundary_budget.py
examples/source_to_intent_research_kernel_ingress_rejection_coverage.py
examples/source_to_intent_research_kernel_ingress_conformance_gate.py
examples/source_to_intent_research_kernel_ingress_diagnostics.py
examples/source_to_intent_research_kernel_ingress_idiom_alignment.py
examples/source_to_intent_research_kernel_ingress_proof_bundle.py
examples/source_to_intent_research_kernel_ingress_evidence_gate.py
examples/source_to_intent_research_source_runtime_smoke.py
examples/source_to_intent_research_readiness.py
examples/external_frontend_package_conformance.py
examples/real_triton_integration_admission_gate.py
examples/source_ingestion_quarantine_gate.py
examples/package_import_sandbox_gate.py
examples/plugin_discovery_allowlist_gate.py
examples/source_to_intent_parser_block_gate.py
```

Key docs:

- [Frontend adapter](docs/FRONTEND_ADAPTER.md)
- [Triton source threat model](docs/TRITON_SOURCE_THREAT_MODEL.md)
- [Triton source preflight](docs/TRITON_SOURCE_PREFLIGHT.md)
- [Triton integration readiness](docs/TRITON_INTEGRATION_READINESS.md)
- [Real Triton Integration Admission Gate](docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md)
- [Real Triton Integration Threat Model](docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md)
- [Source Ingestion Quarantine Gate](docs/SOURCE_INGESTION_QUARANTINE_GATE.md)
- [Package Import Sandbox Gate](docs/PACKAGE_IMPORT_SANDBOX_GATE.md)
- [Plugin Discovery Allowlist Gate](docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md)
- [Source-To-Intent next syntax slice](docs/SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE.md)
- [External frontend package conformance](docs/EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE.md)
- [Source Intent schema](docs/SOURCE_INTENT_SCHEMA.md)
- [Source Intent axis attributes](docs/SOURCE_INTENT_AXIS_ATTRIBUTES.md)
- [Source Intent frontend conformance gate](docs/SOURCE_INTENT_FRONTEND_CONFORMANCE_GATE.md)
- [Source Intent return semantics](docs/SOURCE_INTENT_RETURN_SEMANTICS.md)
- [Source Intent runtime returns](docs/SOURCE_INTENT_RUNTIME_RETURNS.md)
- [Source-to-Intent corpus evidence](docs/SOURCE_TO_INTENT_CORPUS.md)
- [Source-to-Intent property corpus](docs/SOURCE_TO_INTENT_PROPERTY_CORPUS.md)
- [Source-to-Intent parser report](docs/SOURCE_TO_INTENT_PARSER_REPORT.md)
- [Source-to-Intent research parser](docs/SOURCE_TO_INTENT_RESEARCH_PARSER.md)
- [Source-to-Intent research parser conformance gate](docs/SOURCE_TO_INTENT_RESEARCH_PARSER_CONFORMANCE_GATE.md)
- [Source-to-Intent research diagnostics](docs/SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS.md)
- [Source-to-Intent research preflight bridge](docs/SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE.md)
- [Source-to-Intent research execution bridge](docs/SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE.md)
- [Source-to-Intent research idiom alignment](docs/SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT.md)
- [Source-to-Intent research evidence gate](docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md)
- [Source-to-Intent research proof bundle](docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md)
- [Kernel Ingress runtime output closure index](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_OUTPUT_CLOSURE_INDEX.md)
- [Kernel Ingress Runtime Replay Verifier Index](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX.md)
- [Source-to-Intent research capability claim](docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM.md)
- [Source-to-Intent research capability claim gate](docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE.md)
- [Source-to-Intent research source runtime smoke](docs/SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE.md)
- [Source-to-Intent research kernel ingress](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md)
- [Source-to-Intent research kernel ingress runtime matrix](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX.md)
- [Source-to-Intent research kernel ingress runtime step trace](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE.md)
- [Source-to-Intent research kernel ingress runtime evidence bundle index](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX.md)
- [Source-to-Intent research kernel ingress backend equivalence](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE.md)
- [Source-to-Intent research kernel ingress backend equivalence shape profiles](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES.md)
- [Source-to-Intent research kernel ingress workload scope](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE.md)
- [Source-to-Intent research kernel ingress runtime coverage policy](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY.md)
- [Source-to-Intent research kernel ingress runtime backend alignment](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT.md)
- [Source-to-Intent research kernel ingress boundary budget](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET.md)
- [Source-to-Intent research kernel ingress rejection coverage](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE.md)
- [Source-to-Intent research kernel ingress conformance gate](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE.md)
- [Source-to-Intent research kernel ingress diagnostics](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS.md)
- [Source-to-Intent research kernel ingress idiom alignment](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT.md)
- [Source-to-Intent research kernel ingress proof bundle](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md)
- [Source-to-Intent research kernel ingress evidence gate](docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md)
- [Source-to-Intent parser block gate](docs/SOURCE_TO_INTENT_PARSER_BLOCK_GATE.md)
- [Source-to-Intent research readiness](docs/SOURCE_TO_INTENT_RESEARCH_READINESS.md)
- [Source-to-Intent parser gate](docs/SOURCE_TO_INTENT_PARSER_GATE.md)

## Backend Authoring

Backends enter TUC as capability data first. Backend execution is allowed only
through explicitly trusted prototype executors.

Current authoring path:

```text
manifest
    -> Manifest Claim Review
    -> Backend Capability Coverage
    -> Backend Registry diagnostics
    -> Compiler decision report
    -> Backend conformance
    -> Backend Author Readiness
```

Current plugin lifecycle boundary:

```bash
python examples/backend_plugin_lifecycle_policy.py
```

This policy keeps external plugin discovery, generated artifact execution, and
native plugin ABI loading blocked. The sandbox model, artifact provenance,
resource budget, fuzz/negative-test evidence, and maintainer approval now exist
as data-only evidence; the lifecycle evidence gate is complete without enabling
execution.

Key docs:

- [Backend API v0.1](docs/BACKEND_API.md)
- [Backend capability schema](docs/BACKEND_CAPABILITY_SCHEMA.md)
- [Backend capability coverage](docs/BACKEND_CAPABILITY_COVERAGE.md)
- [Manifest Claim Review](docs/MANIFEST_CLAIM_REVIEW.md)
- [Backend Author Evidence Gate](docs/BACKEND_AUTHOR_EVIDENCE_GATE.md)
- [Backend Plugin Lifecycle Policy](docs/BACKEND_PLUGIN_LIFECYCLE_POLICY.md)
- [Backend Plugin Sandbox Model](docs/BACKEND_PLUGIN_SANDBOX_MODEL.md)
- [Backend Plugin Artifact Provenance](docs/BACKEND_PLUGIN_ARTIFACT_PROVENANCE.md)
- [Backend Plugin Resource Budget](docs/BACKEND_PLUGIN_RESOURCE_BUDGET.md)
- [Backend Plugin Fuzz Negative Tests](docs/BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS.md)
- [Backend Plugin Maintainer Approval](docs/BACKEND_PLUGIN_MAINTAINER_APPROVAL.md)

## Performance Boundaries

TUC currently proves correctness and inspectability, not native performance
parity.

Native performance claims remain blocked even though the current Kernel Ingress
proof slice now has accepted executable-backend security review metadata.
Existing Kernel Ingress governance, policy, scope, methodology, provenance,
comparison, planner, break-even, leaky-abstraction, benchmark artifact
inventory, executable-surface review, and golden evidence remain review
metadata, not a native performance proof.

Current readiness evidence marks accepted, digest-pinned performance RFC,
threshold-policy, acceptance-criteria, benchmark artifact manifest metadata,
and executable-backend security review metadata present, along with
Kernel-Ingress-derived workload scope, break-even workload estimates, benchmark
methodology, native-baseline provenance candidates, blocked native comparison
metadata, digest-bound versioned toolchain environment evidence, correctness
goldens, planner-overhead phase separation, leaky-abstraction boundary evidence,
runtime-plan goldens, compiler-decision goldens, and the fail-closed baseline
benchmark report schema. Readiness can be metadata-complete while native
performance claims stay blocked. The Performance Proof Interpretation report is
the next gate: it records that readiness is true while accepted measurement
interpretation artifacts are still not supplied.

The planner-overhead portfolio evidence is generated by
`examples/planner_overhead_portfolio.py` and documented in
`docs/PLANNER_OVERHEAD_PORTFOLIO.md`.

Key docs:

- [Performance proof boundary](docs/PERFORMANCE_PROOF_BOUNDARY.md)
- [Performance proof readiness](docs/PERFORMANCE_PROOF_READINESS.md)
- [Performance proof interpretation](docs/PERFORMANCE_PROOF_INTERPRETATION.md)
- [Planner overhead report](docs/PLANNER_OVERHEAD_REPORT.md)
- [Planner overhead portfolio](docs/PLANNER_OVERHEAD_PORTFOLIO.md)
- [Leaky abstraction report](docs/LEAKY_ABSTRACTION_REPORT.md)
- [Executable backend security review](docs/EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT.md)
- [Backend Plugin Lifecycle Policy](docs/BACKEND_PLUGIN_LIFECYCLE_POLICY.md)
- [Backend Plugin Sandbox Model](docs/BACKEND_PLUGIN_SANDBOX_MODEL.md)
- [Backend Plugin Artifact Provenance](docs/BACKEND_PLUGIN_ARTIFACT_PROVENANCE.md)
- [Backend Plugin Resource Budget](docs/BACKEND_PLUGIN_RESOURCE_BUDGET.md)
- [Backend Plugin Fuzz Negative Tests](docs/BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS.md)
- [Backend Plugin Maintainer Approval](docs/BACKEND_PLUGIN_MAINTAINER_APPROVAL.md)

## Governance

TUC is pre-alpha. APIs, IR names, backend contracts, and runtime behavior are
expected to change as the project moves from prototype proof toward a stable
hardware-independent compute interface.

Project controls:

- Apache-2.0 license.
- RFC process for architecture changes.
- CODEOWNERS-backed review boundaries.
- Branch protection guidance.
- CI, security scanning, SBOM/checksum release artifacts, and Trusted
  Publishing governance.

Key docs:

- [Contributing](CONTRIBUTING.md)
- [Governance](GOVERNANCE.md)
- [Security baseline](docs/SECURITY_BASELINE.md)
- [Review policy](docs/REVIEW_POLICY.md)
- [Release governance](docs/RELEASE_GOVERNANCE.md)
- [Branch protection policy](docs/BRANCH_PROTECTION.md)

## Quickstart

```powershell
docker compose build dev
docker compose run --rm dev bash
```

```bash
pytest -q
python examples/proof_of_execution.py
```

## Repository Layout

```text
docs/       Project documentation
examples/   Runnable prototype examples
rfcs/       Design proposals and accepted decisions
src/tuc/    TUC Python package
tests/      Unit and golden tests
```

## License

TUC is licensed under the [Apache License 2.0](LICENSE).
