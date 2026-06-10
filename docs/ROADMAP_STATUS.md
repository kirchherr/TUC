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
- Runtime operation semantic contract checks for MVP operation shapes, axes,
  scalar-output rejection, and supported elementwise kernels.
- Runtime tensor value contract checks for declared shapes, `float64` dtype,
  and finite values at input and output boundaries.

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
  input validation, partition-plan matching, output-shape checks, unsupported
  executor rejection, and deterministic execution traces.
- Proof-of-execution golden at `tests/golden/proofs/proof_of_execution.txt` and
  execution-trace golden at
  `tests/golden/execution_traces/proof_of_execution.txt`.
- Triton metadata MVP-family execution trace golden at
  `tests/golden/execution_traces/triton_metadata_mvp_families.txt`.
- Trusted runtime backend contract golden at
  `tests/golden/runtime_backend_contracts/trusted_runtime_executor_registry.txt`.
- Runtime execution readiness golden at
  `tests/golden/execution_readiness/proof_of_execution.txt`.
- Runtime Executor negative tests for input shape mismatch, non-`float64`
  inputs, non-finite inputs, and non-finite outputs.
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
  data.
- Machine-readable Source Intent Frontend Conformance report JSON Schema at
  `schemas/source_intent_frontend_conformance_report.v0.schema.json`.
- Source-To-Intent Parser Gate defining the required future parser RFC,
  budgets, accepted/rejected corpus, deterministic diagnostics, goldens,
  HAC-IR neutrality review, and conformance evidence before source text may
  create `source_intent.v0` plain data.
- Source-To-Intent Readiness report with deterministic blocked golden evidence
  for future parser proposals.
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
  Conformance report matching the report schema before maintainers consider
  any source-text parser or frontend package integration.
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
