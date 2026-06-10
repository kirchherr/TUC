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
- `tests/golden/proofs/proof_of_abstraction.txt`
- `tests/golden/proofs/proof_of_reduction.txt`
- `tests/golden/proofs/proof_of_softmax.txt`
- `docs/PROOF_OF_ABSTRACTION.md`
- `docs/PROOF_OF_REDUCTION.md`
- `docs/PROOF_OF_SOFTMAX.md`

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
- Baseline benchmark reports are schema-versioned diagnostic artifacts with an
  explicit non-performance-claim boundary.
- Planner-overhead reports separate compiler/planner phases from execution
  timing and keep break-even claims blocked.
- Leaky-abstraction reports keep hardware-specific performance facts assigned
  to homes outside HAC-IR.
- Native-baseline provenance reports identify native comparison candidates as
  bounded review data while keeping native performance claims blocked.

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
- Softmax operation-family planning defines the review gate for future
  nonlinear proof graphs and softmax-specific score components.
- Runtime-plan goldens cover the softmax proof graph's fallback assignment and
  cross-domain transfer bytes.

Next work:

- Add candidate scoring once transfer/noise-aware models are stable.
- Add runtime-plan golden dumps for future proof graphs only when they add new
  placement or transfer evidence.
- Add richer override diagnostics only if they stay bounded and golden-tested.
- Add noise/error-budget score components only after those models are stable and
  documented.

Go/No-Go:

- Every operation assignment has an inspectable reason.
- Movement costs are explicit.
- Fallbacks do not hide semantic changes.
- Runtime planning remains deterministic for test fixtures.

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
- Leaky Abstraction Report for diagnostic HAC-IR boundary review.
- Native Baseline Provenance Report for diagnostic native comparison
  provenance.
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
- Performance claims remain blocked until leaky-abstraction evidence,
  planner-overhead evidence, native baseline provenance, correctness goldens,
  security review, and a passing Performance Proof Readiness report exist.
- Baseline benchmark reports must remain diagnostic-only unless a future native
  benchmark RFC adds separate provenance, artifact, and security gates.
- Planner-overhead reports must keep execution timing and break-even workload
  claims explicit rather than hidden in aggregate benchmark numbers.
- Leaky-abstraction reports must keep hardware-specific performance facts out
  of HAC-IR even when those facts are required for future native speed.
- Native-baseline provenance reports must remain data-only and must not include
  host paths, command lines, backend artifacts, raw output, or device-specific
  identifiers.

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
