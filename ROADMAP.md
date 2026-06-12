# TUC Roadmap

## Strategic Priority

The [TUC Master Plan](TUC_MASTER_PLAN.md) leads this roadmap.

TUC is **The Universal Compute**. The compiler pipeline is an implementation
tool inside TUC, not the project's identity.

The roadmap answers one question:

```text
How do we prove that compute intent can flow through a hardware-independent
interface into capability-driven runtime planning and correct execution?
```

Roadmap items are accepted when they strengthen at least one of the strategic
assets:

- HAC-IR as hardware-neutral compute intent.
- Backend capability descriptions as hardware self-description.
- Runtime planning as explainable placement and movement reasoning.
- Open integration as the path for future hardware vendors.

## Roadmap Rules

Before any roadmap item is accepted, ask:

1. Does this increase hardware independence?
2. Does this strengthen or protect HAC-IR?
3. Would a future hardware vendor benefit from this without changing TUC core?
4. Can the result be inspected, tested, and reproduced?
5. Does it avoid new compiler attack surfaces such as plugin discovery, dynamic
   imports, subprocess execution, or generated-artifact execution?

If the answer to the first question is no, the item is not core roadmap work.

## Non-Goals For Version 1

- No complete Triton fork.
- No production CUDA, HIP, photonic, or neuromorphic backend.
- No performance-parity claim against vendor libraries.
- No native performance parity claim before
  [Performance Proof Boundary](docs/PERFORMANCE_PROOF_BOUNDARY.md) is
  satisfied and
  [Performance Proof Readiness Report](docs/PERFORMANCE_PROOF_READINESS.md)
  passes.
- No auto-discovery or execution of third-party backend plugins.
- No arbitrary PyTorch model support.
- No native parser, native MLIR dialect, or executable artifact path without a
  dedicated security RFC, fuzzing plan, and sandboxing model.

## Proof Ladder

Each phase maps to the proof ladder from the master plan.

| Level | Meaning | TUC Evidence |
| --- | --- | --- |
| 0 | Architecture | Master plan, RFCs, documented boundaries |
| 1 | Prototype | In-repository Python implementation |
| 2 | Proof | Working example with correct result |
| 3 | Validation | Golden output and reproducible test |
| 4 | Integration | External-style backend author path |
| 5 | Adoption | Organization-ready integration surface |

## Phase Alpha: Smallest Unarguable Proof

Status: active and partially complete.

Purpose: prove the central claim before expanding scope.

Target:

```text
Graph
    ->
HAC-IR
    ->
Runtime Planning
    ->
Backend A
    ->
Backend B
    ->
Correct Result
```

Required artifacts:

- `examples/proof_of_abstraction.py`
- `examples/proof_of_reduction.py`
- `examples/proof_of_softmax.py`
- `examples/proof_of_execution.py`
- `examples/proof_of_systolic_execution.py`
- `examples/systolic_manifest_path.py`
- `examples/runtime_backend_equivalence.py`
- `examples/runtime_vector_backend_equivalence.py`
- `examples/runtime_mixed_backend_equivalence.py`
- `tests/golden/proofs/proof_of_abstraction.txt`
- `tests/golden/proofs/proof_of_reduction.txt`
- `tests/golden/proofs/proof_of_softmax.txt`
- `tests/golden/proofs/proof_of_execution.txt`
- `tests/golden/proofs/proof_of_systolic_execution.txt`
- `tests/golden/proofs/systolic_manifest_path.txt`
- `tests/golden/runtime_backend_equivalence/current_report.json`
- `tests/golden/runtime_backend_equivalence/vector_sim_report.json`
- `tests/golden/runtime_backend_equivalence/mixed_accelerators.json`
- `tests/golden/execution_traces/proof_of_execution.txt`
- `docs/PROOF_OF_ABSTRACTION.md`
- `docs/PROOF_OF_REDUCTION.md`
- `docs/PROOF_OF_SOFTMAX.md`
- `docs/PROOF_OF_EXECUTION.md`
- `docs/SYSTOLIC_SIMULATOR.md`
- `docs/RUNTIME_EXECUTOR.md`

Completed evidence:

- Input graph is declared as compute intent.
- HAC-IR dump is deterministic.
- Runtime plan assigns matmul to `linear-sim` and elementwise fallback to the
  neutral `reference-cpu` backend.
- Transfer plan is inspectable.
- Result matches independent NumPy reference semantics.
- Golden proof output validates full stdout.
- Golden runtime-plan output validates placement and transfer reasoning.
- Second proof graph covers `matmul -> reduction -> elementwise` with a
  correct independent NumPy reference result.
- Golden HAC-IR and runtime-plan output validate the second proof independently
  from its full report.
- Third proof graph covers `matmul -> softmax` with explicit axis validation,
  correct independent NumPy reference semantics, explainable fallback, and
  transfer-plan evidence.
- Proof reports include deterministic metadata for proof version, graph family,
  and backend set.
- Proof artifact changes have a reviewer-facing checklist and merge gate.
- Performance proof boundaries are documented: Objective Alpha proves
  correctness and inspectability, not native performance parity.
- Performance proof readiness is machine-readable and intentionally blocked
  until leaky-abstraction, planner-overhead, native-baseline, benchmark-artifact,
  and executable-backend security evidence exists.
- Performance-proof RFC reports track future native performance claim proposals,
  acceptance status, evidence links, security review IDs, and digests while
  keeping native performance claims blocked.
- Performance claim threshold policy reports require accepted, digest-pinned
  threshold metadata before "near native" or percentage claims can be reviewed.
- Performance acceptance criteria reports require accepted, digest-pinned
  pass/fail metadata before benchmark artifacts can count as passing evidence.
- Triton idiom coverage reports track which Triton-like idioms are covered by
  schema-versioned metadata examples and golden evidence while direct source
  ingestion remains blocked.
- Runtime Executor v0 executes already-compiled graphs through a fixed trusted
  in-process prototype executor registry and emits deterministic execution
  traces.
- Runtime Executor MVP-family trace covers `matmul`, `softmax`, `reduction`,
  and `elementwise` through the Triton-like metadata graph.
- Trusted Runtime Backend Executor Contract v0 exposes the fixed in-process
  executor registry as deterministic pure data and keeps artifact execution,
  device access, dynamic loading, subprocesses, JIT, and network access
  forbidden.
- Runtime execution readiness reports validate runtime plans against trusted
  backend executor contracts before any operation executes.
- Triton-like MVP metadata graph readiness evidence covers `matmul`,
  `softmax`, `reduction`, and `elementwise` before execution.
- Runtime Evidence Matrix v0 inventories HAC-IR, runtime-plan,
  compiler-decision, readiness, trace, and correctness evidence across current
  graph fixtures with deterministic schema and golden output; the current
  matrix is complete across all accepted graph fixtures.
- Runtime Executor Conformance v0 verifies the fixed trusted executor registry
  against MVP operation-family support and rejection behavior with deterministic
  schema and golden output.
- Runtime Evidence Gate v0 composes the complete runtime evidence matrix and
  trusted executor conformance into the main CI job.
- Systolic simulator proof targets `systolic-sim`, records `device_sram`
  placement and `blocked -> row_major` layout conversion, executes through the
  trusted runtime executor, and validates against independent reference
  semantics.
- Systolic Tensor Store Evidence records planned `device_sram` and `blocked`
  value-record metadata for the `systolic-sim` output while keeping raw values
  omitted by policy.
- Runtime Backend Equivalence executes the same neutral graph as a
  `reference-cpu` baseline and as a `systolic-sim` candidate placement, proving
  matched terminal output metadata without serializing tensor values.
- Vector simulator backend evidence adds a trusted `vector-sim` placement for
  `softmax -> reduction -> elementwise`, proving a second non-CPU accelerator
  family can preserve terminal output semantics without serializing tensor
  values.
- Runtime Evidence Gate binds the vector simulator equivalence fixture, so the
  `reference-cpu` versus `vector-sim` proof slice is merge-relevant rather than
  standalone demonstration-only evidence.
- Mixed backend equivalence executes one graph as `reference-cpu` baseline and
  as a `systolic-sim -> vector-sim -> vector-sim -> vector-sim` candidate,
  proving two non-CPU trusted accelerator families can compose in one plan
  while preserving terminal output semantics.
- Systolic capability manifest path loads `systolic-sim` from explicit JSON
  capability data for planning while execution remains authorized only through
  the trusted Runtime Executor registry.
- Objective Alpha abstraction, reduction, and softmax proofs now execute through
  Runtime Executor v0 and emit readiness and trace goldens before their
  correctness result is accepted.
- Proof-of-execution now has separate HAC-IR, runtime-plan, and
  compiler-decision goldens, so its full proof report is independently
  reviewable across every matrix evidence layer.
- Runtime operation semantic contracts validate MVP operation shapes, axes, and
  supported elementwise kernels before trusted kernels run.
- Runtime tensor value contracts enforce declared shapes, `float64` dtype, and
  finite values at input and output boundaries for trusted prototype execution.
- Runtime value records now carry planned backend, memory-domain, layout, and
  placement-source metadata, with Tensor Store Evidence checking those fields
  against the accepted Partition Plan.
- Proof-of-execution compiles, plans, executes, traces, and verifies a graph
  against independent reference semantics without plugin discovery, device
  access, subprocesses, JIT, or generated-artifact execution.
- Baseline benchmark reports are schema-versioned diagnostic artifacts with an
  explicit non-performance-claim boundary.
- Planner-overhead reports separate compiler/planner phases from execution
  timing and keep break-even claims blocked.
- Break-even workload-size reports identify future planning-amortization
  thresholds as bounded metadata while keeping planner-benefit claims blocked.
- Leaky-abstraction reports keep hardware-specific performance facts assigned
  to homes outside HAC-IR.
- Native-baseline provenance reports identify native comparison candidates as
  bounded review data while keeping native performance claims blocked.
- Native-baseline comparison reports identify bounded comparison metadata
  between TUC baseline artifacts and native benchmark artifacts without loading
  raw outputs.
- Benchmark-artifact manifest reports inventory future benchmark report
  artifacts through bounded IDs and digests without loading raw outputs.
- Workload-scope reports bound future performance claims to explicit operation
  families, shape profiles, dtype policies, problem-size ranges, and correctness
  references.
- Benchmark-methodology reports define measurement clocks, iteration policies,
  statistic policy, isolation, outlier handling, and reproducibility policy
  before benchmark numbers can become evidence.
- Toolchain-environment reports identify versioned runtime, package, compiler,
  driver, container, and OS components without host discovery.
- Executable-backend security review reports identify future executable
  surfaces, threat models, sandbox models, budgets, provenance, fuzzing
  evidence, and maintainer approval without approving execution.

Next work:

- Expand future proof graph families only when the existing proof contracts
  remain stable.

Go/No-Go:

- The proof must end with `PASS`.
- The full report must be reproducible.
- The proof must not rely on real hardware, network access, plugin discovery,
  dynamic imports, or generated-artifact execution.

## Phase Beta: HAC-IR Contract

Status: in progress.

Purpose: make the hardware-independent interface stronger than any individual
backend.

Deliverables:

- HAC-IR semantic charter: what belongs in HAC-IR and what is forbidden.
- Reserved `tuc.*` attribute policy.
- Operation-family contracts for matmul, elementwise, reduction, and softmax.
- Data-movement attributes as compiler-produced facts.
- Error-budget attributes as intent and planning constraints.
- Negative tests for hardware-specific leakage into HAC-IR.
- Deterministic HAC-IR golden dumps for proof and MVP graphs.

Completed evidence:

- `docs/HAC_IR_SEMANTIC_CHARTER.md` separates compute intent, compiler facts,
  planning constraints, and forbidden backend details.
- `docs/HAC_IR_NEUTRALITY.md` defines the reviewer-facing neutrality checklist.
- `HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES` rejects known high-risk vendor, device,
  plugin, backend-artifact, and specialized-placement leakage.
- Negative tests verify that hardware-specific `tuc.*` attributes fail closed
  before backend assignment or lowering can treat them as valid facts.
- Deterministic HAC-IR golden dumps cover the Objective Alpha proof graph and
  the Phase 1 MVP graph.
- Deterministic HAC-IR golden dumps cover the second reduction proof graph.
- Deterministic HAC-IR golden dumps cover the third softmax proof graph.
- Softmax operation-family planning documents stable reference semantics,
  HAC-IR boundaries, runtime decomposition gates, and proof requirements before
  softmax proof goldens are introduced.

Next work:

- Add future HAC-IR golden dumps only when new proof graph families add
  contract value beyond abstraction, reduction, and softmax.

Go/No-Go:

- HAC-IR can express MVP compute intent without naming vendor hardware.
- Unknown reserved attributes fail closed.
- Hardware-specific details stay in capabilities, manifests, HS-IR, backend
  implementations, or runtime plans.

## Phase Gamma: Capability Framework

Status: in progress.

Purpose: let hardware describe what it can do without forcing implementation
details into HAC-IR.

Deliverables:

- Schema-versioned backend capability manifests.
- Explicit backend capability registry.
- Pure-data backend support diagnostics.
- Backend conformance fixtures.
- Backend author certification checklist.
- Negative test template for backend authors.
- Capability examples for simulator, explicit GPU backends, neutral fallback,
  and future specialized
  backends.

Completed evidence:

- External-style backend author path demonstrates manifest loading, explicit
  registry diagnostics, compiler planning, reusable conformance, and trusted
  lowering without modifying TUC core.
- Backend conformance reports can be emitted as deterministic JSON artifacts
  for maintainer review.
- Backend capability schema assumptions for error budgets, latency, energy,
  calibration, and noise modeling are documented separately from HAC-IR and
  executable backend behavior.
- Capability-schema negative examples show which backend claims are invalid or
  misleading and keep those cases covered by tests.
- Compiler decision reports connect backend support diagnostics to final
  runtime assignments.
- The systolic manifest path proves that specialized accelerator capabilities
  can be described as data, planned, readiness-checked, and executed through a
  pre-existing trusted runtime contract without plugin discovery.
- Manifest Claim Review blocks syntactically valid but overreaching
  specialized accelerator manifests before they become accepted planning
  evidence.
- The external backend author path runs Manifest Claim Review before registry
  loading, compiler planning, conformance, or trusted lowering.
- Backend Author Readiness summarizes the external author path as one
  schema-versioned pass/fail evidence artifact.
- Backend Author Evidence Gate composes manifest claim review and backend
  author readiness as a CI-facing check.
- Golden compiler decision-report fixtures cover proof and MVP graphs.
- Softmax operation-family planning defines what future softmax capability,
  runtime, and decision-report fixtures must prove.
- Golden compiler decision-report fixtures cover the softmax proof graph's
  explicit fallback and rejected backend support evidence.

Next work:

- Add future decision-report fixtures only when new proof graph families or
  capability claims introduce new backend-selection evidence.

Go/No-Go:

- A toy backend can be described through capability data.
- Unsupported operations and layouts are rejected explicitly.
- Specialized accelerator manifests pass claim review before acceptance.
- External backend author onboarding fails closed when claim review blocks a
  manifest.
- External backend author onboarding has one deterministic readiness report.
- External backend author onboarding evidence is checked by CI.
- Capability checks never import backend code, run subprocesses, load dynamic
  libraries, touch devices, or execute artifacts.

## Phase Delta: Runtime Planning

Status: in progress.

Purpose: make placement decisions explainable before making them clever.

Deliverables:

- Runtime partition plans.
- Transfer edges and transfer-cost profiles.
- Layout conversion accounting.
- Produced-layout metadata.
- Backend decision reports.
- Golden runtime-plan dumps.
- Planning diagnostics that explain why work executes where it does.

Completed evidence:

- [Runtime manual override policy](docs/RUNTIME_OVERRIDE_POLICY.md) blocks
  automatic global optimization from gaining hidden placement controls before
  schema, validation, review, decision-report, and runtime-plan golden gates are
  defined.
- Schema-versioned `RuntimeOverrideSet` data can constrain operation placement
  only across already accepted backend candidates and is covered by negative
  tests plus compiler decision-report and runtime-plan golden fixtures.
- Opt-in `CandidateScore` diagnostics expose deterministic transfer, layout,
  and preferred-domain score components without changing default placement
  behavior.
- Runtime Candidate Score Evidence reports verify default score silence,
  opt-in score emission, compiler decision-report parity, and selected/rejected
  candidate visibility.
- Runtime Candidate Scoring Policy reports fix the active comparator order and
  keep noise, error-budget, calibration, and benchmark score inputs blocked
  until separately modeled.
- Runtime Candidate Scoring Conformance reports verify that the current
  planner's observable candidate choices match the active comparator policy.
- Runtime Candidate Scoring Gate composes score evidence, scoring policy, and
  conformance as one CI-facing runtime-planning check.
- Runtime Buffer Lifetime reports expose conservative produced tensor
  lifetimes, peak live bytes, and exact-match reuse candidates before adding an
  allocator.
- Runtime Allocation Plan reports expose deterministic tensor-to-slot bindings,
  reuse slots, reserved bytes, and allocation metadata digests before adding a
  real allocator.
- Runtime Memory Budget reports bind to Allocation Plan metadata digests and
  check explicit memory-domain budgets before adding memory pools or device
  allocation.
- Runtime Allocation Request Manifest reports expose bounded, data-only future
  allocator admission requests without runtime handles.
- Runtime Memory Planning Gate verifies allocation-plan, memory-budget,
  allocation-request-manifest, and lifetime/allocation/budget/request digest
  binding evidence before allocator behavior can be accepted.
- Softmax operation-family planning defines the review gate for future
  nonlinear proof graphs and softmax-specific score components.
- Runtime-plan goldens cover the softmax proof graph's fallback assignment and
  cross-domain transfer bytes.

Next work:

- Add candidate scoring once transfer/noise-aware models are stable.
- Use Runtime Candidate Scoring Policy as the review contract before changing
  candidate-score comparator semantics.
- Keep Runtime Candidate Scoring Conformance passing before changing candidate
  score comparator behavior.
- Keep Runtime Candidate Scoring Gate passing before accepting richer
  candidate-scoring behavior.
- Add runtime-plan golden dumps for future proof graphs only when they add new
  placement or transfer evidence.
- Add richer override diagnostics only if they stay bounded and golden-tested.
- Add allocator behavior only after allocation-plan, memory-budget, and
  allocation-request-manifest evidence stays deterministic, digest-bound, and
  reviewable.
- Add noise/error-budget score components only after those models are stable and
  documented.

Go/No-Go:

- Every operation assignment has an inspectable reason.
- Movement costs are explicit.
- Fallbacks do not hide semantic changes.
- Runtime planning remains deterministic for test fixtures.
- Candidate score diagnostics remain evidence, not hidden automatic global
  optimization.

## Phase Epsilon: Real Triton Integration

Status: future credibility milestone.

Purpose: show that TUC can ingest real developer-facing compute intent.

Deliverables:

- Triton compatibility matrix.
- Triton-like metadata adapter hardening.
- Execution-free Triton source preflight with bounded diagnostics.
- Triton source preflight fuzz/property corpus.
- Source Intent Frontend Conformance report for external frontend authors.
- Source Intent Frontend Conformance report JSON Schema.
- Source-To-Intent Parser Gate for future source parser proposals.
- Source-To-Intent Readiness report for parser proposal evidence.
- First real Triton kernel ingestion path.
- MVP kernel family coverage: matmul, elementwise, reduction, softmax-like.
- Correctness tests against deterministic references.
- Optional performance baselines, treated as diagnostic data rather than the
  core success metric.
- Baseline benchmark report schema for diagnostic-only timing artifacts.
- Planner Overhead Report for diagnostic compiler/planner phase separation.
- Break-Even Workload Size Report for diagnostic planning-amortization
  metadata.
- Leaky Abstraction Report for diagnostic HAC-IR boundary review.
- Native Baseline Provenance Report for diagnostic native comparison
  provenance.
- Native Baseline Comparison Report for diagnostic native comparison metadata.
- Benchmark Artifact Manifest Report for diagnostic benchmark artifact
  inventory.
- Workload Scope Report for diagnostic workload-family and problem-size
  boundaries.
- Benchmark Methodology Report for diagnostic measurement policy review.
- Toolchain Environment Report for diagnostic versioned environment review.
- Executable Backend Security Review Report for diagnostic executable-surface
  security review.
- Performance Proof RFC Report for diagnostic claim-proposal governance before
  benchmark artifacts can support a native performance claim.
- Performance Claim Threshold Policy Report for diagnostic threshold governance
  before benchmark artifacts can support "near native" or percentage claims.
- Performance Acceptance Criteria Report for diagnostic pass/fail governance
  before benchmark artifacts can count as proof evidence.
- Performance proof boundary covering leaky abstraction and planner overhead
  before native performance claims.
- Performance Proof Readiness report for future native performance proposal
  evidence.

Go/No-Go:

- Real Triton-style intent reaches HAC-IR without executing untrusted user code
  during metadata ingestion.
- Frontend intake is schema-versioned, bounded, and reviewable before any
  source parser, Python import, or `@triton.jit` handling is accepted.
- MVP operation-family coverage is demonstrated through frontend-originated
  metadata goldens before direct Triton syntax support is attempted.
- Direct Triton source parsing is blocked until a threat model, parser budgets,
  negative tests, fuzzing or property-test corpus, deterministic diagnostics,
  and sandboxing gates are in place.
- Source preflight may inspect syntax as data, but it must not produce
  `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, or backend decisions.
- Preflight fuzz/property tests must keep arbitrary decoded source, invalid
  Unicode, and malicious seed cases fail-closed before source-intent IR work.
- Source Intent Intake may build `SourceIntentModule` only from already decoded
  schema-versioned plain data, not source text, files, preflight reports, or
  Python objects.
- Source Intent plain data must have a machine-readable schema artifact for
  external frontend authors; runtime validation remains fail-closed in TUC.
- Source Intent Intake fuzz/property tests must keep arbitrary JSON-like data,
  hostile source-text keys, backend hints, and broken tensor references
  fail-closed before source parsers can target the schema.
- Source Intent Intake proof artifacts must show the accepted plain-data path
  through metadata intake, HAC-IR, runtime planning, and compiler decision
  reports before any source-text parser targets the schema.
- Canonical Source Intent IR remains a data-only contract; conversion to
  metadata is allowed only through the separately reviewed
  `source_intent_to_metadata.execution_free.v0` adapter and its goldens.
- Source Intent IR to metadata conversion may start only from an already
  constructed `SourceIntentModule`; source text and preflight reports remain
  disconnected until a separate source-to-intent security gate is accepted.
- External frontend authors must first provide Source Intent Frontend
  Conformance evidence for accepted plain data and rejected hostile cases,
  using the versioned conformance report schema.
- Source-to-intent parser proposals must satisfy the Source-To-Intent Parser
  Gate before source text can create `source_intent.v0` plain data.
- Source-to-intent parser proposals must pass the Source-To-Intent Readiness
  report before source text can influence compiler artifacts.
- Existing Triton compatibility is preserved within MVP scope.
- The integration strengthens the hardware-independent interface rather than
  turning TUC into a Triton fork.
- Triton idiom coverage must be represented through
  `schemas/triton_idiom_coverage_report.v0.schema.json` before source syntax or
  `@triton.jit` integration is considered.
- Performance claims remain blocked until leaky-abstraction evidence,
  planner-overhead evidence, native baseline provenance, native baseline
  comparison, correctness goldens, security review, an accepted bounded
  Performance Proof RFC Report, an accepted bounded Performance Claim
  Threshold Policy Report, an accepted bounded Performance Acceptance Criteria
  Report, and a passing Performance Proof Readiness report exist.
- Baseline benchmark reports must remain diagnostic-only unless a future native
  benchmark RFC adds separate provenance, artifact, and security gates.
- Performance proof RFC reports must remain data-only and must not include raw
  benchmark output, raw timing samples, host paths, command lines, environment
  variables, device identifiers, backend artifacts, generated code, native
  source contents, or execution permission.
- Performance claim threshold policy reports must remain data-only and must not
  include raw benchmark output, raw timing samples, host paths, command lines,
  environment variables, device identifiers, backend artifacts, generated code,
  native source contents, or execution permission.
- Performance acceptance criteria reports must remain data-only and must not
  include raw benchmark output, raw timing samples, host paths, command lines,
  environment variables, device identifiers, backend artifacts, generated code,
  native source contents, or execution permission.
- Planner-overhead reports must keep execution timing and break-even workload
  claims explicit rather than hidden in aggregate benchmark numbers.
- Break-even workload-size reports must remain data-only and must not include
  host paths, command lines, raw timing samples, raw native output, backend
  artifacts, device identifiers, benchmark report contents, or generated code.
- Leaky-abstraction reports must keep hardware-specific performance facts out
  of HAC-IR even when those facts are required for future native speed.
- Native-baseline provenance reports must remain data-only and must not include
  host paths, command lines, backend artifacts, raw output, or device-specific
  identifiers.
- Native-baseline comparison reports must remain data-only and must not include
  host paths, command lines, raw timing samples, raw native output, backend
  artifacts, device identifiers, benchmark report contents, or generated code.
- Benchmark-artifact manifest reports must remain data-only and must not include
  host paths, URLs, raw timing samples, backend binaries, generated code, or
  embedded benchmark outputs.
- Workload-scope reports must remain data-only and must not include tensors,
  host paths, raw benchmark output, backend artifacts, device identifiers, or
  hardware-specific performance knobs.
- Benchmark-methodology reports must remain data-only and must not include raw
  timing samples, host paths, environment variables, backend artifacts, device
  identifiers, or generated code.
- Toolchain-environment reports must remain data-only and must not include host
  paths, environment variables, secrets, package-manager output, device
  identifiers, backend binaries, or generated code.
- Executable-backend security review reports must remain data-only and must not
  include host paths, environment variables, backend artifact contents, device
  identifiers, dynamic-library paths, native source contents, generated code, or
  execution permission.

## Phase Zeta: Specialized Hardware Proofs

Status: future proof expansion.

Purpose: prove that HAC-IR is not merely "GPU plus simulator".

Candidate proof tracks:

- Photonic simulator: linear algebra, transfer costs, noise assumptions,
  calibration data.
- Neuromorphic simulator: sparse connectivity, event/update approximation,
  routing/configuration artifacts.
- Additional accelerators: only after capability contracts remain neutral.

Deliverables:

- Specialized capability manifests.
- Simulator-backed correctness reports.
- Noise/error-budget reports.
- Runtime plans that split linear and nonlinear work explicitly.
- Documentation showing which assumptions are backend-specific and therefore
  kept out of HAC-IR.

Go/No-Go:

- Specialized backends improve the proof of hardware independence.
- No specialized backend can redefine HAC-IR semantics for its own convenience.
- Numerical correctness and reproducibility are required before performance or
  energy claims.

## Phase Eta: External Integration And Governance

Status: future ecosystem readiness.

Purpose: make TUC usable by people who are not the original authors.

Deliverables:

- Organization-backed maintainer groups.
- CODEOWNERS backed by teams rather than a single maintainer.
- Backend author onboarding guide with a reproducible certification path.
- Versioned capability and runtime-plan schemas.
- Release artifacts with SBOM, checksums, and provenance.
- PyPI Trusted Publishing and protected tag governance.

Go/No-Go:

- An external developer can add and test a toy backend without modifying TUC
  core.
- Governance protects HAC-IR neutrality from vendor capture.
- Release and supply-chain controls are in place before broad adoption.

## Current Priority Order

1. Keep the master plan and roadmap aligned.
2. Maintain the proof-of-abstraction validation as the first public proof.
3. Harden HAC-IR neutrality and reserved-attribute rejection.
4. Strengthen backend capability and conformance tooling.
5. Make runtime planning explanations richer and golden-tested.
6. Integrate real Triton intent only after the abstraction proof remains stable.
7. Expand to specialized hardware simulators only when they strengthen the
   universal compute claim.

## Success Metrics

Measure:

- Reproducible proof milestones.
- HAC-IR neutrality and stability.
- Backend onboarding effort.
- Runtime planning explainability.
- Correctness against independent references.
- Security of input boundaries and backend integration surfaces.

Do not optimize roadmap decisions for:

- GitHub stars.
- Raw benchmark wins.
- Vendor-specific feature depth.
- Social reach.
- Premature hardware-specific performance claims.

## Strategic Risks

### Risk: Becoming Another Compiler

Mitigation: every phase must preserve the master-plan framing: compiler work is
only useful when it advances hardware-independent compute.

### Risk: Vendor Capture

Mitigation: keep vendor details outside HAC-IR and route them through
capabilities, manifests, HS-IR, backend implementations, and runtime plans.

### Risk: Architecture Inflation

Mitigation: no architecture without a runnable artifact or an explicit security
gate.

### Risk: Simulator Illusion

Mitigation: simulator demos must include numerical correctness, independent
references, and reproducible golden reports.

### Risk: Runtime Planning Complexity

Mitigation: keep rule-based deterministic planning until candidate scoring is
testable and explainable.

### Risk: Leaky Abstraction And Planner Overhead

Mitigation: do not claim native performance parity until
[Performance Proof Boundary](docs/PERFORMANCE_PROOF_BOUNDARY.md) is satisfied
and
[Performance Proof Readiness Report](docs/PERFORMANCE_PROOF_READINESS.md)
passes.
Hardware-specific optimization details must stay outside HAC-IR, and planning
overhead must be measured separately from execution time.

### Risk: Insecure Plugin Surface

Mitigation: do not add auto-discovery, dynamic imports, dynamic libraries,
subprocesses, device access, or artifact execution without a dedicated security
RFC, sandbox model, and negative tests.
