# TUC

TUC is **The Universal Compute**: an early-stage open-source prototype exploring
whether compute intent can be represented through a hardware-independent
interface.

The goal is not to build another compiler. The goal is to prove that software
can describe compute intent while hardware describes capabilities, with TUC
performing the translation through HAC-IR, backend capability data, and runtime
planning.

The strategic north star is [TUC Master Plan](TUC_MASTER_PLAN.md). Roadmap and
implementation decisions should strengthen hardware independence, protect
HAC-IR, and move the project up the proof ladder.

## What TUC Is Trying To Prove

The first credible claim is intentionally narrow:

> Compute intent can be represented independently of hardware, planned across
> backend capabilities, and checked against deterministic reference semantics
> without changing mathematical intent.

The current prototype contains:

- A small hardware-agnostic compute model.
- Developer-facing compilation hints.
- Backend capability metadata.
- A simulator backend for linear algebra operations.
- Rule-based runtime partitioning.
- Proof-of-abstraction example for Objective Alpha.
- Proof-of-reduction example for Objective Alpha's second graph family.
- Proof-of-softmax example for Objective Alpha's nonlinear operation family.
- Data-movement-aware HAC-IR metadata for MVP kernels.
- Runtime transfer-plan dumps with prototype transfer-cost estimates.
- Validated transfer-cost profiles and backend-produced layout metadata.
- Backend API v0.1 authoring guide for external prototype backends.
- Explicit backend capability registry for manifest-loaded planning data.
- Backend author certification checklist and negative-test template.
- External-style backend author path for manifest, registry, compiler,
  conformance, and trusted lowering.
- Deterministic backend conformance report artifacts for maintainer review.
- Backend capability schema guidance for error budgets, latency, energy,
  calibration, and noise assumptions.
- Capability-schema negative examples for invalid or misleading backend claims.
- Compiler decision reports connecting backend support diagnostics to runtime
  assignments.
- Golden compiler decision-report fixtures for proof and MVP graph review.
- Runtime manual override policy for future placement constraints before
  automatic global optimization.
- Schema-versioned runtime manual overrides for operation-scoped placement
  constraints across already accepted backend candidates.
- Opt-in runtime candidate score diagnostics for reviewable placement evidence.
- Softmax operation-family planning contract and proof graph fixtures.
- Backend conformance fixtures for prototype operation semantics and diagnostics.
- Branch protection policy for `main` and required CI/security checks.
- Release artifact workflow with CycloneDX SBOM, SHA-256 checksums, and
  GitHub artifact attestations.
- Release governance policy with SHA-pinned release actions and publishing
  approval requirements.
- PyPI Trusted Publishing job gated by protected `v*` tags and the `pypi`
  environment.
- CODEOWNERS-backed review policy for compiler, runtime, backend, governance,
  and release trust boundaries.
- Proof-report metadata for proof version, graph family, and backend set.
- Runtime-plan golden dump fixtures for reviewer-visible compiler contracts.
- HAC-IR golden dump fixtures for proof and MVP graph contract review.
- Schema-versioned JSON manifests for backend capabilities and transfer profiles.
- Golden-kernel correctness fixtures for MVP operation semantics.
- Prototype Triton-like metadata adapter for frontend ingestion.
- Triton source threat model that blocks direct Python source, decorator, and
  `@triton.jit` ingestion until a bounded data-only parser gate exists.
- Execution-free Triton source preflight with parser budgets, negative tests,
  and deterministic report goldens before any source-to-IR conversion.
- Triton source preflight fuzz/property corpus for arbitrary decoded bytes,
  invalid Unicode, seed combinations, and bounded diagnostics.
- Diagnostic Triton idiom coverage reports that track metadata examples and
  golden evidence while direct source ingestion remains blocked.
- Deterministic Triton idiom coverage golden report for reviewer-visible
  frontend coverage evidence.
- Runtime Executor v0 with trusted in-process prototype backend execution and
  deterministic execution traces.
- Runtime Executor MVP-family trace covering `matmul`, `softmax`, `reduction`,
  and `elementwise` through the Triton-like metadata graph.
- Trusted Runtime Backend Executor Contract v0 with golden evidence for the
  fixed in-process prototype executor registry.
- Runtime execution readiness reports that gate planned execution against
  trusted backend contracts before kernels run.
- Triton-like MVP metadata graph readiness evidence across `matmul`,
  `softmax`, `reduction`, and `elementwise` before execution.
- Runtime Evidence Matrix v0 with schema-versioned, data-only proof inventory
  for HAC-IR, runtime-plan, compiler-decision, readiness, trace, and correctness
  evidence, now complete across current graph fixtures.
- Runtime Executor Conformance v0 with schema-versioned golden evidence for
  trusted executor support and rejection behavior.
- Objective Alpha proof graphs for abstraction, reduction, and softmax now emit
  Runtime Execution Readiness and Execution Trace evidence before `PASS`.
- Runtime operation semantic checks for MVP operation shapes, axes, and
  elementwise kernels before trusted kernels run.
- Runtime tensor value contract checks for declared shapes, `float64` dtype,
  and finite values at input and output boundaries.
- Proof-of-execution example that compiles, plans, executes, traces, and
  verifies a graph against independent reference semantics.
- CPU-first baseline benchmark harness with explicit CUDA capability status.
- Schema-versioned diagnostic baseline benchmark reports that are explicitly
  marked as non-performance-proof artifacts.
- Diagnostic planner-overhead reports that separate compiler/planner phases
  from execution timing.
- Diagnostic break-even workload-size reports that track future amortization
  thresholds without embedding raw timing samples.
- Diagnostic leaky-abstraction reports that keep hardware-specific performance
  facts outside HAC-IR.
- Diagnostic native-baseline provenance reports that identify future native
  comparison candidates without executing native code or claiming parity.
- Diagnostic native-baseline comparison reports that track bounded comparison
  metadata without loading raw benchmark outputs.
- Diagnostic benchmark-artifact manifest reports that inventory benchmark
  report artifacts through bounded IDs and digests.
- Diagnostic workload-scope reports that bound future performance claims to
  explicit operation families, shape profiles, dtype policies, and problem sizes.
- Diagnostic benchmark-methodology reports that define measurement clocks,
  iteration policy, statistic policy, isolation, and reproducibility policy.
- Diagnostic toolchain-environment reports that identify versioned runtime,
  package, compiler, driver, container, and OS components without host discovery.
- Diagnostic executable-backend security review reports that track future
  executable surfaces without approving execution.
- Diagnostic performance-proof RFC reports that track future native performance
  claim proposals, acceptance status, evidence links, and digests.
- Diagnostic performance claim threshold policy reports that make "near native"
  or percentage claims require accepted, digest-pinned threshold policy first.
- Diagnostic performance acceptance criteria reports that make performance
  pass/fail rules explicit before benchmark artifacts can count as evidence.
- Performance proof boundary and readiness report for leaky-abstraction,
  planner-overhead, native baseline, native comparison, benchmark artifact, and
  executable-backend security evidence before native performance claims.
- Native-MLIR-oriented HAC-IR design spike.
- HAC-IR v0 dialect contracts for operations and compiler attributes.
- HAC-IR semantic charter for compute intent, compiler facts, planning
  constraints, and forbidden backend details.
- HAC-IR neutrality guardrails against backend, vendor, device, plugin, and
  artifact leakage.
- HS-IR v0 contracts for backend assignments, produced layouts, and transfer summaries.
- Tests and a runnable Phase 0 vertical-slice example.
- Docker-based compiler development environment.
- RFC, governance, issue, PR, and CI scaffolding.

## Repository Layout

```text
.
|-- docs/                 Project documentation
|-- docker/               Development container files
|-- examples/             Runnable prototype examples
|-- rfcs/                 Design proposals and accepted architecture decisions
|-- scripts/              Local helper scripts
|-- src/tuc/              TUC Python package
|-- tests/                Unit tests
|-- ROADMAP.md            Strategic implementation roadmap
`-- pyproject.toml        Python project metadata and tooling config
```

## Quickstart

Build the development image:

```powershell
docker compose build dev
```

Open a development shell:

```powershell
docker compose run --rm dev bash
```

Run tests inside the container:

```bash
pytest -q
```

Run the Phase 0 vertical slice:

```bash
python examples/phase0_vertical_slice.py
```

Run the Phase 1 IR pipeline skeleton:

```bash
python examples/phase1_ir_pipeline.py
```

Run the proof-of-abstraction example:

```bash
python examples/proof_of_abstraction.py
```

Run the proof-of-reduction example:

```bash
python examples/proof_of_reduction.py
```

Run the proof-of-softmax example:

```bash
python examples/proof_of_softmax.py
```

Run the proof-of-execution example:

```bash
python examples/proof_of_execution.py
```

Inspect the runtime evidence matrix:

```bash
python examples/runtime_evidence_matrix.py
```

Inspect trusted runtime executor conformance:

```bash
python examples/runtime_executor_conformance.py
```

Run the Runtime Evidence Gate used by CI:

```bash
python examples/runtime_evidence_gate.py
```

Inspect data-movement metadata:

```bash
python examples/data_movement_ir.py
```

Run the Triton-like metadata adapter example:

```bash
python examples/triton_metadata_adapter.py
```

Run the execution-free Triton source preflight example:

```bash
python examples/triton_source_preflight.py
```

Inspect Triton idiom coverage through metadata and golden evidence:

```bash
python examples/triton_idiom_coverage_report.py
```

Run the Backend API v0.1 authoring example:

```bash
python examples/backend_api_v0.py
```

Run the explicit backend registry example:

```bash
python examples/backend_registry.py
```

Run the external-style backend author path:

```bash
python examples/external_backend_author_path.py
```

Run the baseline benchmark harness:

```bash
python scripts/benchmark.py --iterations 2 --warmup 1
```

Inspect the intentionally blocked performance proof readiness report:

```bash
python examples/performance_proof_readiness.py
```

Inspect the diagnostic performance-proof RFC report:

```bash
python examples/performance_proof_rfc_report.py
```

Inspect the diagnostic performance claim threshold policy report:

```bash
python examples/performance_claim_threshold_policy_report.py
```

Inspect the diagnostic performance acceptance criteria report:

```bash
python examples/performance_acceptance_criteria_report.py
```

Inspect the diagnostic planner-overhead report:

```bash
python examples/planner_overhead_report.py
```

Inspect the diagnostic break-even workload-size report:

```bash
python examples/break_even_workload_size_report.py
```

Inspect the diagnostic leaky-abstraction report:

```bash
python examples/leaky_abstraction_report.py
```

Inspect the diagnostic native-baseline provenance report:

```bash
python examples/native_baseline_provenance.py
```

Inspect the diagnostic native-baseline comparison report:

```bash
python examples/native_baseline_comparison_report.py
```

Inspect the diagnostic benchmark-artifact manifest report:

```bash
python examples/benchmark_artifact_manifest.py
```

Inspect the diagnostic workload-scope report:

```bash
python examples/workload_scope_report.py
```

Inspect the diagnostic benchmark-methodology report:

```bash
python examples/benchmark_methodology_report.py
```

Inspect the diagnostic toolchain-environment report:

```bash
python examples/toolchain_environment_report.py
```

Inspect the diagnostic executable-backend security review report:

```bash
python examples/executable_backend_security_review_report.py
```

Verify the MLIR design-spike artifact:

```bash
python scripts/verify_mlir_spike.py
```

Prepare local release artifacts:

```bash
python -m build
python scripts/generate_sbom.py --output dist/tuc.cdx.json
python scripts/write_artifact_checksums.py dist --output dist/SHA256SUMS
```

Inspect example backend and transfer manifests:

```text
examples/manifests/
```

## Local Python Setup

The Docker environment is recommended. If you already have Python 3.11+:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

## Documentation

- [TUC Master Plan](TUC_MASTER_PLAN.md)
- [Roadmap](ROADMAP.md)
- [Development environment](docs/DEVELOPMENT_ENVIRONMENT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Phase 0 plan](docs/PHASE_0.md)
- [MVP definition](docs/MVP.md)
- [Proof of abstraction](docs/PROOF_OF_ABSTRACTION.md)
- [Proof of reduction](docs/PROOF_OF_REDUCTION.md)
- [Proof of softmax](docs/PROOF_OF_SOFTMAX.md)
- [Proof of execution](docs/PROOF_OF_EXECUTION.md)
- [Runtime Executor v0](docs/RUNTIME_EXECUTOR.md)
- [Runtime Executor Conformance](docs/RUNTIME_EXECUTOR_CONFORMANCE.md)
- [Runtime evidence matrix](docs/RUNTIME_EVIDENCE_MATRIX.md)
- [Runtime Evidence Gate](docs/RUNTIME_EVIDENCE_GATE.md)
- [Proof artifact review checklist](docs/PROOF_ARTIFACT_REVIEW.md)
- [Performance proof boundary](docs/PERFORMANCE_PROOF_BOUNDARY.md)
- [Performance proof readiness report](docs/PERFORMANCE_PROOF_READINESS.md)
- [Performance proof RFC report](docs/PERFORMANCE_PROOF_RFC_REPORT.md)
- [Performance claim threshold policy report](docs/PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT.md)
- [Performance acceptance criteria report](docs/PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT.md)
- [Planner overhead report](docs/PLANNER_OVERHEAD_REPORT.md)
- [Break-even workload size report](docs/BREAK_EVEN_WORKLOAD_SIZE_REPORT.md)
- [Leaky abstraction report](docs/LEAKY_ABSTRACTION_REPORT.md)
- [Native baseline provenance report](docs/NATIVE_BASELINE_PROVENANCE.md)
- [Native baseline comparison report](docs/NATIVE_BASELINE_COMPARISON_REPORT.md)
- [Benchmark artifact manifest report](docs/BENCHMARK_ARTIFACT_MANIFEST.md)
- [Workload scope report](docs/WORKLOAD_SCOPE_REPORT.md)
- [Benchmark methodology report](docs/BENCHMARK_METHODOLOGY_REPORT.md)
- [Toolchain environment report](docs/TOOLCHAIN_ENVIRONMENT_REPORT.md)
- [Executable backend security review report](docs/EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT.md)
- [MVP kernels](docs/MVP_KERNELS.md)
- [Softmax operation-family planning](docs/SOFTMAX_OPERATION_PLANNING.md)
- [Golden kernel correctness](docs/GOLDEN_KERNELS.md)
- [Triton-like metadata adapter](docs/FRONTEND_ADAPTER.md)
- [Triton idiom coverage report](docs/TRITON_IDIOM_COVERAGE_REPORT.md)
- [Triton compatibility](docs/TRITON_COMPATIBILITY.md)
- [Triton source threat model](docs/TRITON_SOURCE_THREAT_MODEL.md)
- [Triton source preflight](docs/TRITON_SOURCE_PREFLIGHT.md)
- [Benchmarking](docs/BENCHMARKING.md)
- [Backend API v0.1](docs/BACKEND_API.md)
- [Backend capability schema](docs/BACKEND_CAPABILITY_SCHEMA.md)
- [Backend capability registry](docs/BACKEND_REGISTRY.md)
- [Compiler decision report](docs/COMPILER_DECISION_REPORT.md)
- [Runtime manual override policy](docs/RUNTIME_OVERRIDE_POLICY.md)
- [Backend author certification](docs/BACKEND_AUTHOR_CERTIFICATION.md)
- [Backend conformance fixtures](docs/BACKEND_CONFORMANCE.md)
- [MLIR design spike](docs/MLIR_DESIGN_SPIKE.md)
- [HAC-IR dialect contract](docs/HAC_IR_DIALECT.md)
- [HAC-IR semantic charter](docs/HAC_IR_SEMANTIC_CHARTER.md)
- [HAC-IR neutrality checklist](docs/HAC_IR_NEUTRALITY.md)
- [HS-IR dialect contract](docs/HS_IR_DIALECT.md)
- [Data movement aware IR](docs/DATA_MOVEMENT_IR.md)
- [Runtime transfer plan](docs/RUNTIME_PLAN.md)
- [Security baseline](docs/SECURITY_BASELINE.md)
- [Branch protection policy](docs/BRANCH_PROTECTION.md)
- [Review policy](docs/REVIEW_POLICY.md)
- [Release security](docs/RELEASE_SECURITY.md)
- [Release governance](docs/RELEASE_GOVERNANCE.md)
- [Roadmap status](docs/ROADMAP_STATUS.md)
- [Contributing](CONTRIBUTING.md)
- [Governance](GOVERNANCE.md)

## Project Status

TUC is pre-alpha. APIs, IR names, backend contracts, and runtime behavior are
expected to change as the project moves from compiler skeleton toward a
hardware-independent compute interface proof.

## License

TUC is licensed under the [Apache License 2.0](LICENSE).
