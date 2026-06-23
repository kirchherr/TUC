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
- `examples/runtime_backend_equivalence_portfolio.py`
- `examples/runtime_backend_equivalence_portfolio_policy.py`
- `examples/runtime_vector_backend_equivalence.py`
- `examples/runtime_mixed_backend_equivalence.py`
- `examples/runtime_hs_ir_plan_alignment.py`
- `tests/golden/proofs/proof_of_abstraction.txt`
- `tests/golden/proofs/proof_of_reduction.txt`
- `tests/golden/proofs/proof_of_softmax.txt`
- `tests/golden/proofs/proof_of_execution.txt`
- `tests/golden/proofs/proof_of_systolic_execution.txt`
- `tests/golden/proofs/systolic_manifest_path.txt`
- `tests/golden/runtime_backend_equivalence/current_report.json`
- `tests/golden/runtime_backend_equivalence/vector_sim_report.json`
- `tests/golden/runtime_backend_equivalence/mixed_accelerators.json`
- `tests/golden/runtime_backend_equivalence/portfolio_report.json`
- `tests/golden/runtime_backend_equivalence/portfolio_policy_report.json`
- `tests/golden/runtime_hs_ir_plan_alignment/mixed_report.json`
- `tests/golden/execution_traces/proof_of_execution.txt`
- `docs/PROOF_OF_ABSTRACTION.md`
- `docs/PROOF_OF_REDUCTION.md`
- `docs/PROOF_OF_SOFTMAX.md`
- `docs/PROOF_OF_EXECUTION.md`
- `docs/SYSTOLIC_SIMULATOR.md`
- `docs/RUNTIME_EXECUTOR.md`
- `docs/RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO.md`
- `docs/RUNTIME_HS_IR_PLAN_ALIGNMENT.md`

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
- Runtime Evidence Matrix now supports graph-scoped required evidence kinds,
  so backend-equivalence fixtures are inventoried honestly under the
  `backend_equivalence` requirement instead of pretending to own full
  proof/readiness/trace evidence.
- Runtime Evidence Gate binds backend-equivalence reports back to their Matrix
  graph entries, so report-level pass status and proof-inventory coverage
  cannot drift apart.
- Mixed Runtime Tensor Store Evidence now records the accepted
  `systolic-sim -> vector-sim -> vector-sim -> vector-sim` plan as read-only
  Runtime Value Record placement metadata, giving the mixed accelerator slice
  an inspectable tensor-store proof without serialized tensor values.
- Runtime Backend Equivalence Portfolio aggregates the systolic, vector, and
  mixed accelerator equivalence reports into one backend-diversity artifact and
  Runtime Evidence Gate binds that aggregate back to the exact reports checked
  in the same invocation.
- Runtime Evidence Matrix inventories the Backend Equivalence Portfolio under
  scoped `backend_equivalence_portfolio` and
  `backend_equivalence_portfolio_policy` requirements, and Runtime Evidence
  Gate verifies that matrix coverage before accepting portfolio evidence.
- Runtime Backend Equivalence Portfolio Policy declares the accepted portfolio
  slice membership, backend sequences, minimum comparison counts, and required
  backend families as data-only evidence, with Runtime Evidence Gate binding
  the policy to the portfolio before accepting backend-diversity evidence.
- Runtime Evidence Gate now binds backend-equivalence and portfolio Matrix
  coverage to exact artifact IDs, so a complete Matrix with the right
  artifact kinds cannot silently point at a different evidence artifact.
- Runtime Evidence Gate Matrix Coverage emits those exact Matrix graph/artifact
  bindings as a schema-versioned JSON audit and the Runtime Evidence Gate
  requires that audit to pass.
- Runtime Evidence Replay Verifier v0 (`examples/runtime_evidence_replay_verifier.py`)
  replay-checks serialized Runtime Execution Evidence Bundle and Runtime
  Execution Output Closure reports by metadata digest without re-running source,
  JIT, plugins, devices, or backend artifacts.
- Runtime HS-IR Plan Alignment binds HS-IR backend/layout decisions to the
  accepted `PartitionPlan` and observed `RuntimeExecutionTrace` for the mixed
  accelerator proof slice without serializing tensor values or adding
  execution surfaces.
- Runtime Evidence Matrix and Runtime Evidence Gate now require Runtime HS-IR
  Plan Alignment for the mixed accelerator proof slice, binding the exact
  `runtime_hs_ir_plan_alignment_mixed` artifact ID before the slice can count
  as merge evidence.
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
- Performance-readiness evidence now marks `performance_proof_rfc`,
  `performance_claim_threshold_policy`, and `performance_acceptance_criteria`
  present only when every accepted Kernel Ingress workload scope is bound to
  accepted, digest-pinned governance metadata while benchmark artifacts,
  executable-surface review, and native performance claims remain separate
  gates.
- Kernel Ingress performance-readiness evidence now marks workload-scope and
  planner-overhead report evidence present by contract-checking the
  shape-profile-derived workload scopes and a bounded planner-overhead report
  for the accepted MVP pipeline graph while keeping native performance claims
  blocked.
- Kernel Ingress performance-readiness evidence now also marks correctness
  goldens, runtime-plan goldens, and compiler-decision report goldens present
  only when the deterministic Kernel Ingress golden matches the generated
  report and every accepted case exposes the corresponding SHA-256 digest.
- Performance-readiness evidence now marks `benchmark_report_schema` present
  only when the baseline benchmark report schema is fail-closed,
  diagnostic-only, native-claim-blocked, and bound to the performance proof
  boundary.
- Performance-readiness evidence now marks `benchmark_report_artifacts` present
  only when all required benchmark artifact kinds are bound to digest-pinned
  repository-golden descriptors while raw output loading, timing validation,
  and native performance claims remain blocked.
- Performance-readiness evidence now marks `benchmark_methodology` present only
  when methodology entries are derived from the accepted Kernel Ingress
  workload scopes and remain policy-only, with no benchmark execution or raw
  timing samples.
- Performance-readiness evidence now marks `versioned_toolchain_environment`
  present only when repository-controlled CI, dependency, Docker, compiler, and
  compose declarations are represented as bounded Toolchain Environment Report
  components with `sha256:` digests and no host discovery.
- Performance-readiness evidence now marks `native_baseline_provenance` present
  only when each accepted Kernel Ingress workload scope is bound to a bounded,
  data-only native baseline candidate while reproduction, artifact digests,
  comparisons, and native claims remain blocked.
- Performance-readiness evidence now marks `native_baseline_comparison` present
  only when each accepted Kernel Ingress workload scope is bound to a bounded,
  data-only comparison reference while measurement, digest validation, artifact
  loading, and native claims remain blocked.
- Performance-readiness evidence now marks `break_even_workload_size` present
  only when each accepted Kernel Ingress workload scope is bound to a bounded,
  `estimated_not_validated` amortization entry while digest validation, timing
  comparison, artifact loading, and planner-benefit claims remain blocked.
- Performance-readiness evidence now marks `leaky_abstraction_report` present
  only when the accepted Kernel Ingress MVP pipeline keeps performance-critical
  facts out of HAC-IR and assigns them to backend capability,
  backend implementation, runtime plan, or compiler decision-report homes.
- Benchmark-methodology reports define measurement clocks, iteration policies,
  statistic policy, isolation, outlier handling, and reproducibility policy
  before benchmark numbers can become evidence.
- Toolchain-environment reports identify versioned runtime, package, compiler,
  driver, container, and OS components without host discovery.
- Executable-backend security review reports identify future executable
  surfaces, threat models, sandbox models, budgets, provenance, fuzzing
  evidence, and maintainer approval without approving execution.
- Performance-readiness evidence now marks `executable_backend_security_review`
  present only when every tracked executable surface is bound to accepted,
  digest-pinned security-review metadata; readiness can be metadata-complete
  while native performance claims remain blocked.
- Performance Proof Interpretation now separates that metadata-complete
  readiness state from native benchmark interpretation, proving that a green
  readiness report still leaves native performance claims blocked until accepted
  measurement-interpretation artifacts exist.

Next work:

- Add accepted measurement-interpretation artifacts only after benchmark
  outputs, timing summaries, planner overhead, and native comparison semantics
  are separately reviewed as data-only evidence.
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
- The forbidden attribute baseline now also blocks vendor execution units,
  warp/wavefront sizes, cache-line and memory-bank details, device UUIDs,
  hardware serials, runtime handles, FPGA bitstreams, vendor libraries, and
  TPU/NPU/ROCm/Metal-family target leaks from HAC-IR.
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
- Backend Capability Coverage emits a schema-versioned pure-data matrix showing
  which simulator capability descriptions cover current MVP operation families
  before conformance or execution begins.
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
- Current simulator capability data covers `matmul`, `elementwise`,
  `reduction`, and `softmax` in one deterministic coverage artifact.
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
- Runtime Allocation Admission reports bind those requests to current Memory
  Budget evidence before any real allocator, memory pool, device allocation, or
  runtime handle can be accepted.
- Runtime Allocation Receipt reports transform admitted requests into
  deterministic dry-run allocation ledger entries without pointers, handles,
  memory pools, or device access.
- Runtime Memory Planning Gate verifies allocation-plan, memory-budget,
  allocation-request-manifest, allocation-admission, allocation-receipt, and
  lifetime/allocation/budget/request/admission/receipt digest binding evidence
  before allocator behavior can be accepted. Runtime Evidence Matrix and
  Runtime Evidence Gate now require the memory-planning artifact set by exact
  artifact ID before the central runtime gate can pass.
- Softmax operation-family planning defines the review gate for future
  nonlinear proof graphs and softmax-specific score components.
- Runtime-plan goldens cover the softmax proof graph's fallback assignment and
  cross-domain transfer bytes.
- Runtime HS-IR Plan Alignment proves the current mixed accelerator HS-IR,
  runtime plan, and trusted execution trace agree on backend sequence,
  produced layouts, and layout-conversion accounting.
- Runtime Evidence Gate checks the Runtime HS-IR Plan Alignment report and
  Matrix artifact binding before accepting the mixed accelerator slice.
- Runtime Planning Explanation reports summarize accepted `PartitionPlan`
  selection kinds, backend sequence, fallback count, candidate-score visibility,
  and movement bytes; Runtime Evidence Matrix and Runtime Evidence Gate now
  bind those reports to the systolic and mixed backend-equivalence slices by
  exact artifact ID.

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
- Explicit Source-To-Intent Research Parser for the first tiny source-buffer to
  `source_intent.v0` proof slice.
- Source-To-Intent Research Parser Conformance Gate binding parser output to
  the reusable Source Intent Frontend Conformance path.
- Source-To-Intent Research Diagnostics for source-free accepted/rejected
  parser diagnostic evidence.
- Source-To-Intent Research Preflight Bridge proving accepted/rejected parser
  diagnostics remain layered behind execution-free Triton Source Preflight.
- Source-To-Intent Research Evidence Gate binding readiness, conformance, and
  diagnostics by digest.
- Source-To-Intent Research Execution Bridge proving accepted parser output can
  reach controlled runtime execution only after Source Intent plain-data
  re-intake.
- Source-To-Intent Research Idiom Alignment proving accepted parser slices stay
  inside already covered Triton-like MVP idioms before broader source syntax
  work can claim coverage.
- Source-To-Intent Research Proof Bundle giving reviewers one digest-only
  source-free artifact for the current safe source-to-runtime research slice.
- Source-To-Intent Research Capability Claim
  (`examples/source_to_intent_research_capability_claim.py`) summarizing the
  currently supported bounded Universal Compute research slice above the proof
  bundle and evidence gates while keeping production parser, native
  performance, hardware certification, arbitrary backend execution, and vendor
  compiler replacement claims blocked.
- Source-To-Intent Research Capability Claim Gate
  (`examples/source_to_intent_research_capability_claim_gate.py`) binding that
  high-level claim into CI and failing closed on claim drift, evidence digest
  drift, source leakage, or unreviewed claim expansion.
- Source-To-Intent Research Source Runtime Smoke proving accepted source buffers
  can run end-to-end through Preflight, parser, Source Intent, runtime, and
  reference correctness.
- Source-To-Intent Research Kernel Ingress proving realistic Triton
  module-shaped source buffers can be validated as data, reduced to one
  explicitly selected kernel function, and executed through the controlled
  source-to-runtime research path.
- Source-To-Intent Research Kernel Ingress Fixture Expansion proving a third
  accepted module-shaped kernel, `matmul_reduction`, through the same
  source-free runtime, conformance, diagnostics, and evidence gates.
- Source-To-Intent Research Kernel Ingress Combined MVP Pipeline proving one
  accepted module-shaped kernel can carry `matmul -> softmax -> reduction ->
  elementwise` through Kernel Ingress, Source Intent, runtime planning,
  trusted execution, reference correctness, and evidence gates without
  widening the default parser path.
- Source-To-Intent Research Kernel Ingress Runtime Matrix
  (`examples/source_to_intent_research_kernel_ingress_runtime_matrix.py`)
  proving accepted realistic module-shaped inputs have explicit runtime
  evidence inventory by backend sequence, terminal output, trace-step count,
  and digest.
- Source-To-Intent Research Kernel Ingress Runtime Step Trace
  (`examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py`)
  proving accepted Kernel Ingress runtime cases expose source-free
  operation-level execution order, planned backend, executor backend, public
  tensor names, output dtype/shape metadata, and plan/trace digests.
- Source-To-Intent Research Kernel Ingress Runtime Evidence Bundle Index
  (`examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py`)
  proving accepted Kernel Ingress runtime cases also build and bind standard
  Runtime Execution Evidence Bundles with tensor-store, input-manifest,
  output-manifest, reference-correctness, and execution-receipt evidence.
- Source-To-Intent Research Kernel Ingress Runtime Output Closure Index
  (`examples/source_to_intent_research_kernel_ingress_runtime_output_closure_index.py`)
  proving accepted Kernel Ingress runtime cases also close their public output
  boundary through Runtime Execution Output Closure before they can strengthen
  the bounded research claim.
- Source-To-Intent Research Kernel Ingress Backend Equivalence
  (`examples/source_to_intent_research_kernel_ingress_backend_equivalence.py`)
  proving accepted Kernel Ingress Source Intent preserves public outputs under
  a neutral `reference-cpu` baseline and capability-selected trusted
  `linear-sim`/`vector-sim` simulator placements.
- Source-To-Intent Research Kernel Ingress Backend Equivalence Shape Profiles
  (`examples/source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.py`)
  proving the same accepted Kernel Ingress Source Intent preserves public
  outputs and reference correctness across `base` and `alternate` declared
  tensor shape profiles without widening the parser or making performance
  claims.
- Source-To-Intent Research Kernel Ingress Workload Scope
  (`examples/source_to_intent_research_kernel_ingress_workload_scope.py`)
  binding those proven shape profiles to diagnostic `workload_scope_report.v0`
  data so future performance proposals have bounded operation-family and
  shape-profile scopes while native performance claims remain blocked.
- Performance Proof Readiness now treats performance RFC, threshold-policy, and
  acceptance-criteria governance as present only after binding all accepted
  Kernel Ingress workload scopes to accepted, digest-pinned metadata;
  benchmark artifacts, executable-surface review, and native performance claims
  remain separate gates.
- Performance Proof Readiness now derives current `workload_scope` and
  `planner_overhead_report` evidence from accepted Kernel Ingress contracts
  instead of hand-coded booleans, and binds correctness, runtime-plan, and
  compiler-decision golden evidence to the deterministic Kernel Ingress golden
  report while all native performance claims remain blocked.
- Performance Proof Readiness now treats the baseline benchmark report schema
  as present only after a fail-closed schema contract check.
- Performance Proof Readiness now treats benchmark report artifacts as present
  only after all required artifact kinds are listed through a digest-bound
  repository-golden manifest; artifact loading, timing validation, and native
  performance claims remain blocked.
- Performance Proof Readiness now treats benchmark methodology as present only
  after binding measurement policy to the accepted Kernel Ingress workload
  scopes; benchmark execution and artifact evidence remain blocked.
- Performance Proof Readiness now treats versioned toolchain environment
  evidence as present only after binding repository-controlled CI, dependency,
  Docker, compiler, and compose declarations to Toolchain Environment Report
  components with SHA-256 digests; host discovery remains blocked.
- Performance Proof Readiness now treats native baseline provenance as present
  only after binding all accepted Kernel Ingress workload scopes to data-only
  native baseline candidates; native reproduction, artifact digests,
  comparison evidence, and native claims remain blocked.
- Performance Proof Readiness now treats native baseline comparison as present
  only after binding all accepted Kernel Ingress workload scopes to data-only
  comparison references; benchmark artifact loading, digest validation, timing
  comparison, and native claims remain blocked.
- Performance Proof Readiness now treats break-even workload size as present
  only after binding all accepted Kernel Ingress workload scopes to bounded,
  estimated amortization entries; CI validation, evidence digests, benchmark
  artifact loading, and planner-benefit claims remain blocked.
- Performance Proof Readiness now treats leaky-abstraction evidence as present
  only after the Kernel Ingress MVP pipeline proves HAC-IR is contract-valid
  and free of forbidden hardware-specific performance facts.
- Source-To-Intent Research Kernel Ingress Runtime Coverage Policy
  (`examples/source_to_intent_research_kernel_ingress_runtime_coverage_policy.py`)
  requiring current accepted runtime cases, backend sequences, terminal outputs,
  trace-step counts, and runtime digest fields before the Kernel Ingress proof
  slice can pass.
- Source-To-Intent Research Kernel Ingress Runtime Backend Alignment
  (`examples/source_to_intent_research_kernel_ingress_runtime_backend_alignment.py`)
  binding accepted backend sequences to trusted Runtime Executor conformance
  before the Kernel Ingress proof slice can pass.
- Source-To-Intent Research Kernel Ingress Boundary Budget proving accepted
  realistic module-shaped source buffers stay inside byte, line, AST-node, and
  AST-depth budgets, and that budget overflow rejects before extraction or
  lowering.
- Source-To-Intent Research Kernel Ingress Rejection Coverage proving current
  diagnostics and boundary-budget rejection surfaces are source-free,
  deterministic, and covered before future ingress syntax can expand.
- Source-To-Intent Research Kernel Ingress Conformance Gate proving accepted
  module-shaped source outputs pass the reusable Source Intent Frontend
  Conformance path before future ingress syntax can expand.
- Source-To-Intent Research Kernel Ingress Diagnostics proving accepted and
  rejected realistic module-shaped source cases remain source-free, bounded,
  and fail-closed before future ingress syntax can expand.
- Source-To-Intent Research Kernel Ingress Idiom Alignment proving accepted
  module-shaped source outputs remain inside already covered Triton MVP idioms
  before future ingress syntax can expand.
- Source-To-Intent Research Kernel Ingress Proof Bundle giving reviewers one
  digest-only source-free artifact for the realistic Kernel Ingress research
  slice before future ingress syntax can expand.
- Source-To-Intent Research Kernel Ingress Evidence Gate proving the focused
  Kernel Ingress proof slice is CI-bound before the global Source-To-Intent
  Research Evidence Gate accepts it.
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
- Performance Proof Interpretation report for the post-readiness gate that
  blocks native claims until accepted measurement interpretation exists.

Go/No-Go:

- Real Triton-style intent reaches HAC-IR without executing untrusted user code
  during metadata ingestion.
- Frontend intake is schema-versioned, bounded, and reviewable before any
  source parser, Python import, or `@triton.jit` handling is accepted.
- MVP operation-family coverage is demonstrated through frontend-originated
  metadata goldens before direct Triton syntax support is attempted.
- General Triton source parsing is blocked until a threat model, parser
  budgets, negative tests, fuzzing or property-test corpus, deterministic
  diagnostics, and sandboxing gates are in place.
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
  disconnected except for explicitly accepted research parser slices whose
  output is still only `source_intent.v0` plain data.
- External frontend authors must first provide Source Intent Frontend
  Conformance evidence for accepted plain data and rejected hostile cases,
  using the versioned conformance report schema.
- Source-to-intent parser proposals must satisfy the Source-To-Intent Parser
  Gate before source text can create `source_intent.v0` plain data, except for
  explicitly scoped research parser slices accepted as evidence with default
  parser intake still blocked.
- Source-to-intent parser proposals must pass the Source-To-Intent Readiness
  report before source text can influence compiler artifacts.
- Parser expansions must extend Source-To-Intent Research Diagnostics with
  source-free accepted and rejected evidence before the expanded syntax counts
  as accepted research parser scope.
- Source-To-Intent Research Readiness now tracks the first narrow parser
  research proposal as complete proposal evidence while keeping the default
  parser block intact.
- Source-To-Intent Corpus Evidence now defines accepted and rejected
  source-buffer fixtures for the first parser proof, covers all MVP operation
  families in accepted cases, and keeps the report data-only with no raw source
  or compiler artifacts.
- Source-To-Intent Property Corpus now defines the fuzz/property obligations
  for the first parser proof and binds them to the source corpus report digest.
- Source-To-Intent Parser Report now provides that final proposal-only golden,
  making the research proposal evidence complete while keeping
  `parser_enabled = false` and source parsing outside the compiler input path.
- Source-To-Intent Research Parser v0 now parses a tiny caller-provided
  Triton-like source subset into validated `source_intent.v0` plain data while
  keeping the default parser path blocked and avoiding metadata, graph,
  runtime-plan, or backend-decision output.
- Source-To-Intent Research Parser Conformance Gate now proves the
  `matmul -> elementwise` parser output slice passes Source Intent Frontend
  Conformance, and Source Intent axis attributes now allow the
  `softmax -> reduction` parser output slice to pass the same gate.
- Source Intent Axis Attributes now define neutral `attributes.axis` semantics
  for `softmax` and `reduction`, including intake validation, metadata
  conversion, schema documentation, and parser-conformance evidence.
- Source-To-Intent Research Diagnostics now binds the accepted parser slices
  and whitelisted rejected source cases to deterministic source-free diagnostic
  evidence with stable rejection reason IDs.
- Source-To-Intent Research Preflight Bridge now separates accepted pipeline,
  preflight rejection, and parser semantic rejection evidence for the same
  diagnostic cases before the parser proof can count as CI-facing evidence.
- Source-To-Intent Research Evidence Gate now binds Research Readiness,
  Research Parser Conformance Gate, and Research Diagnostics by SHA-256 digest
  before the current research parser scope counts as CI-facing proof evidence.
- Source-To-Intent Research Execution Bridge now executes the accepted
  `matmul -> elementwise` and `softmax -> reduction` parser slices through
  Source Intent re-intake, metadata conversion, runtime planning, Runtime
  Executor, and Runtime Reference Correctness without exposing raw values or
  parser compiler shortcuts.
- Source-To-Intent Research Idiom Alignment now binds those accepted parser
  slices to existing Triton Idiom Coverage and the Execution Bridge by digest,
  so parser scope cannot silently expand beyond proven MVP operation families.
- Source-To-Intent Research Proof Bundle now indexes the current readiness,
  conformance, diagnostics, Preflight Bridge, Execution Bridge, Idiom
  Alignment, Source Runtime Smoke, Kernel Ingress, Kernel Ingress Runtime
  Matrix, Kernel Ingress Conformance, Kernel Ingress Diagnostics, Kernel
  Ingress Idiom Alignment, Kernel Ingress Proof Bundle, and Evidence Gate
  artifacts by digest for review.
- Source-To-Intent Research Source Runtime Smoke now proves the accepted
  `matmul -> elementwise` and `softmax -> reduction` source buffers can execute
  end-to-end through the controlled research parser path without opening
  general Triton source ingestion.
- Source-To-Intent Research Kernel Ingress now proves realistic Triton
  module-shaped source buffers with the accepted Triton import prelude and one
  explicitly selected `@triton.jit` kernel can execute end-to-end through the
  controlled research path without evaluating imports, decorators, JIT, files,
  devices, plugins, or general module execution.
- Source-To-Intent Research Kernel Ingress Boundary Budget now records ingress
  byte, line, AST-node, AST-depth, and diagnostics budgets; accepted module
  observations stay within budget and byte/line budget overflows reject before
  extraction or lowering.
- Source-To-Intent Research Kernel Ingress Rejection Coverage now binds
  diagnostics rejection IDs and boundary-budget rejection IDs into one
  source-free coverage matrix before the Kernel Ingress Proof Bundle can pass.
- Source-To-Intent Research Kernel Ingress Runtime Matrix now binds accepted
  module-shaped source cases to backend sequences, terminal output names,
  trace-step counts, runtime plan digests, execution trace digests, reference
  correctness digests, and the Kernel Ingress E2E digest.
- Source-To-Intent Research Kernel Ingress Runtime Step Trace now binds
  accepted runtime matrix cases to operation-level planned/executed backend
  steps, public tensor names, output dtype/shape metadata, and the combined
  `mvp_pipeline` path without exposing raw source or tensor values.
- Source-To-Intent Research Kernel Ingress Runtime Evidence Bundle Index now
  binds accepted runtime step-trace cases to the standard Runtime Execution
  Evidence Bundle sections, including tensor store, manifests, reference
  correctness, and execution receipt digests.
- Source-To-Intent Research Kernel Ingress Runtime Output Closure Index now
  binds accepted Kernel Ingress runtime cases to Runtime Execution Output
  Closure, requiring public output metadata to close across Output Contract,
  Public Output Bundle, Runtime Execution Receipt, and Runtime Execution
  Evidence Bundle before the Kernel Ingress claim can pass.
- Source-To-Intent Research Kernel Ingress Backend Equivalence now compares
  accepted Kernel Ingress Source Intent cases under a neutral `reference-cpu`
  baseline and capability-selected `linear-sim`/`vector-sim` placements,
  proving terminal public output metadata is preserved without exposing raw
  source or tensor values.
- Source-To-Intent Research Kernel Ingress Runtime Coverage Policy now binds
  the runtime matrix to required accepted cases, operation families, backend
  sequences, terminal outputs, trace-step count policy, and runtime digest
  fields before Kernel Ingress proof evidence can pass.
- Source-To-Intent Research Kernel Ingress Runtime Backend Alignment now binds
  the runtime matrix and coverage policy to trusted Runtime Executor
  conformance for `linear-sim` and `vector-sim`, so accepted backend sequences
  are not merely unchecked string labels.
- Source-To-Intent Research Kernel Ingress Conformance Gate now proves accepted
  module-shaped source outputs are ordinary Source Intent frontend payloads that
  pass accepted-case conformance and rejected backend-hint/source-text escape
  checks.
- Source-To-Intent Research Kernel Ingress Diagnostics now binds accepted
  module-shaped source cases and rejected module surfaces to stable source-free
  reason IDs for unsupported imports, import-from statements, multiple kernel
  functions, top-level side effects, and kernel-name mismatches.
- Source-To-Intent Research Kernel Ingress Idiom Alignment now binds accepted
  module-shaped Kernel Ingress outputs to existing Triton Idiom Coverage and
  the Kernel Ingress Conformance Gate by digest, so realistic input shape does
  not silently expand beyond proven MVP operation families.
- Source-To-Intent Research Kernel Ingress Proof Bundle now gives reviewers one
  digest-only source-free index for Kernel Ingress E2E, runtime-matrix,
  runtime-coverage-policy, runtime-backend-alignment, boundary-budget,
  rejection-coverage, diagnostics, conformance, and idiom-alignment evidence
  before the global proof bundle accepts the realistic module-shaped ingress
  claim.
- Source-To-Intent Research Kernel Ingress Evidence Gate now validates Kernel
  Ingress E2E, runtime-matrix, runtime-coverage-policy,
  runtime-backend-alignment, boundary-budget, rejection-coverage, diagnostics,
  conformance, idiom-alignment, and proof-bundle digest bindings as CI-facing
  evidence.
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
2. Keep the first public entry path short through
   [Research Onboarding Slice](docs/RESEARCH_ONBOARDING_SLICE.md) and
   [Research Onboarding Evidence](docs/RESEARCH_ONBOARDING_EVIDENCE.md).
3. Apply external feedback through bounded triage, starting with
   [External Review Triage 2026-06-22](docs/EXTERNAL_REVIEW_TRIAGE_2026_06_22.md).
4. Maintain the proof-of-abstraction validation as the first public proof,
   including the
   [Objective Alpha Public Proof Bundle](docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE.md).
5. Keep HAC-IR neutrality and reserved-attribute rejection hardened as new
   proof and frontend surfaces appear.
6. Strengthen backend capability and conformance tooling.
7. Extend planning explanation coverage only when new proof slices add
   distinct placement, fallback, or movement evidence.
8. Integrate real Triton intent only after the abstraction proof remains stable.
9. Expand to specialized hardware simulators only when they strengthen the
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
