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
- Baseline benchmark harness that can run with or without CUDA.
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
  metadata intake contract before any source parser or `@triton.jit` handling
  is accepted.
- Future softmax decomposition only after runtime/HS-IR planning evidence,
  capability diagnostics, and proof goldens stay inspectable.
- Candidate scoring only after transfer/noise-aware models are stable and its
  decisions can be explained next to manual override effects.
- Noise/error-budget score components only after those models are documented
  outside HAC-IR semantics and covered by goldens.
- Maintainer teams or organization-backed owner groups before broad external
  contribution.
- Plugin lifecycle RFC and sandboxing model before any executable backend
  discovery, artifact execution, or native plugin ABI.
