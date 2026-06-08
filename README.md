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
- Data-movement-aware HAC-IR metadata for MVP kernels.
- Runtime transfer-plan dumps with prototype transfer-cost estimates.
- Validated transfer-cost profiles and backend-produced layout metadata.
- Backend API v0.1 authoring guide for external prototype backends.
- Explicit backend capability registry for manifest-loaded planning data.
- Backend author certification checklist and negative-test template.
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
- Runtime-plan golden dump fixtures for reviewer-visible compiler contracts.
- Schema-versioned JSON manifests for backend capabilities and transfer profiles.
- Golden-kernel correctness fixtures for MVP operation semantics.
- Prototype Triton-like metadata adapter for frontend ingestion.
- CPU-first baseline benchmark harness with explicit CUDA capability status.
- Native-MLIR-oriented HAC-IR design spike.
- HAC-IR v0 dialect contracts for operations and compiler attributes.
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

Inspect data-movement metadata:

```bash
python examples/data_movement_ir.py
```

Run the Triton-like metadata adapter example:

```bash
python examples/triton_metadata_adapter.py
```

Run the Backend API v0.1 authoring example:

```bash
python examples/backend_api_v0.py
```

Run the explicit backend registry example:

```bash
python examples/backend_registry.py
```

Run the baseline benchmark harness:

```bash
python scripts/benchmark.py --iterations 2 --warmup 1
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
- [MVP kernels](docs/MVP_KERNELS.md)
- [Golden kernel correctness](docs/GOLDEN_KERNELS.md)
- [Triton-like metadata adapter](docs/FRONTEND_ADAPTER.md)
- [Triton compatibility](docs/TRITON_COMPATIBILITY.md)
- [Benchmarking](docs/BENCHMARKING.md)
- [Backend API v0.1](docs/BACKEND_API.md)
- [Backend capability registry](docs/BACKEND_REGISTRY.md)
- [Backend author certification](docs/BACKEND_AUTHOR_CERTIFICATION.md)
- [Backend conformance fixtures](docs/BACKEND_CONFORMANCE.md)
- [MLIR design spike](docs/MLIR_DESIGN_SPIKE.md)
- [HAC-IR dialect contract](docs/HAC_IR_DIALECT.md)
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
