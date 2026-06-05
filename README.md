# TUC

TUC is an early-stage open-source prototype for a Triton Universal Compiler.

The goal is to keep Triton-style developer ergonomics while exploring a compiler
and runtime architecture that can target heterogeneous AI accelerators:
conventional GPUs first, then simulator-backed photonic and neuromorphic targets.

TUC is currently moving through Phase 1. The repository is being shaped as a
serious open-source project while the first compiler pipeline skeleton becomes
real.

## What TUC Is Trying To Prove

The first credible claim is intentionally narrow:

> Existing Triton-style compute intent can be represented in a hardware-agnostic
> compute IR, partitioned across backend capabilities, and lowered into at least
> one conventional or simulated backend without changing mathematical intent.

The current prototype contains:

- A small hardware-agnostic compute model.
- Developer-facing compilation hints.
- Backend capability metadata.
- A simulator backend for linear algebra operations.
- Rule-based runtime partitioning.
- Data-movement-aware HAC-IR metadata for MVP kernels.
- Runtime transfer-plan dumps with prototype transfer-cost estimates.
- Validated transfer-cost profiles and backend-produced layout metadata.
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

Inspect data-movement metadata:

```bash
python examples/data_movement_ir.py
```

## Local Python Setup

The Docker environment is recommended. If you already have Python 3.11+:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

## Documentation

- [Roadmap](ROADMAP.md)
- [Development environment](docs/DEVELOPMENT_ENVIRONMENT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Phase 0 plan](docs/PHASE_0.md)
- [MVP definition](docs/MVP.md)
- [MVP kernels](docs/MVP_KERNELS.md)
- [Triton compatibility](docs/TRITON_COMPATIBILITY.md)
- [Data movement aware IR](docs/DATA_MOVEMENT_IR.md)
- [Runtime transfer plan](docs/RUNTIME_PLAN.md)
- [Security baseline](docs/SECURITY_BASELINE.md)
- [Roadmap status](docs/ROADMAP_STATUS.md)
- [Contributing](CONTRIBUTING.md)
- [Governance](GOVERNANCE.md)

## Project Status

TUC is pre-alpha. APIs, IR names, backend contracts, and runtime behavior are
expected to change as the project moves through Phase 1.

## License

TUC is licensed under the [Apache License 2.0](LICENSE).
