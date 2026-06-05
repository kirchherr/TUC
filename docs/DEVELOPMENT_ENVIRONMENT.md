# Development Environment

This repository ships a Docker-based TUC development environment. The default image is CPU-first and compiler-first, so it can be used for MLIR, IR design, backend API work, tests, and simulators without requiring a local GPU runtime.

## What Is Included

- Ubuntu 24.04
- Python virtual environment in `/opt/tuc-venv`
- Python developer tooling: pytest, ruff, mypy, hypothesis, pybind11, lit, FileCheck
- LLVM 18, Clang 18, LLD 18, LLDB 18
- MLIR 18 tools and CMake packages
- PyTorch installed through a configurable wheel index
- Triton installed from pip

## Build

From the repository root:

```powershell
docker compose build dev
```

Or use the helper:

```powershell
.\scripts\dev.cmd build
```

## Open A Shell

```powershell
docker compose run --rm dev bash
```

Or:

```powershell
.\scripts\dev.cmd shell
```

## Verify The Toolchain

```powershell
.\scripts\dev.cmd check
```

The check prints Python, Clang, LLVM, MLIR, PyTorch, Triton, NumPy, and whether PyTorch sees CUDA.

## Run Baseline Benchmarks

The baseline benchmark harness runs in the default CPU container:

```powershell
docker compose run --rm dev python scripts/benchmark.py --iterations 2 --warmup 1
```

CUDA is reported as explicit capability status until an executable CUDA backend
contract exists.

## Run The CI Smoke Surface Locally

The required `python` CI job runs:

```powershell
docker compose run --rm dev ruff check .
docker compose run --rm dev mypy src/tuc
docker compose run --rm dev pytest -q
docker compose run --rm dev python examples/phase0_vertical_slice.py
docker compose run --rm dev python examples/phase1_ir_pipeline.py
docker compose run --rm dev python examples/data_movement_ir.py
docker compose run --rm dev python examples/triton_metadata_adapter.py
docker compose run --rm dev python examples/backend_api_v0.py
docker compose run --rm dev python scripts/benchmark.py --iterations 1 --warmup 0
```

## Run The Backend API Example

```powershell
docker compose run --rm dev python examples/backend_api_v0.py
```

The example shows a trusted in-process prototype backend with declarative
capabilities, runtime planning, HS-IR assignment, and explicit lower-time
capability rejection.

## Verify Backend Author Negative Tests

```powershell
docker compose run --rm dev pytest -q tests/test_backend_author_negative_template.py
```

The template covers malicious manifest fields, duplicate manifest keys,
unsupported schema versions, false capability claims, unsupported layouts, and
lower-time operation rejection.

## Verify Backend Conformance Fixtures

```powershell
docker compose run --rm dev pytest -q tests/test_backend_conformance.py
```

The conformance fixtures check capability/lowering agreement, semantic artifact
markers, and bounded diagnostics for trusted in-process prototype backends.

## Verify The MLIR Design Spike

```powershell
docker compose run --rm dev python scripts/verify_mlir_spike.py
```

The verifier checks the repository-owned MLIR spike artifact with `mlir-opt` and
the unregistered dialect path.

## Verify HAC-IR Dialect Contracts

```powershell
docker compose run --rm dev pytest -q tests/test_hac_ir_dialect_contracts.py
```

The tests check the Python-level HAC-IR v0 operation and attribute contracts
that future native MLIR definitions must preserve.

## Verify HS-IR Dialect Contracts

```powershell
docker compose run --rm dev pytest -q tests/test_hs_ir_contracts.py
```

The tests check backend assignment, produced-layout, movement-summary, and
runtime-transfer-summary contracts for HS-IR v0.

## Optional GPU Shell

If Docker Desktop has NVIDIA GPU support configured, use:

```powershell
docker compose --profile gpu run --rm gpu bash
```

Or:

```powershell
.\scripts\dev.cmd gpu-shell
```

The default PyTorch index is CPU-only:

```text
https://download.pytorch.org/whl/cpu
```

For a CUDA wheel index, override `PYTORCH_INDEX_URL` before building. Example:

```powershell
$env:PYTORCH_INDEX_URL = "https://download.pytorch.org/whl/cu128"
docker compose build dev
```

## Skip PyTorch During Image Build

For a smaller compiler-only image:

```powershell
$env:INSTALL_TORCH = "0"
docker compose build dev
```

## Notes

- The repository is mounted into the container at `/workspace`.
- `PYTHONPATH` includes `/workspace/src`, which is where the first TUC Python package should live.
- LLVM and MLIR CMake package paths are exported as `LLVM_DIR` and `MLIR_DIR`.
- The image intentionally starts with a stable CPU workflow. GPU acceleration can be enabled once the host Docker/NVIDIA setup is verified.
- A PowerShell helper is also available at `scripts/dev.ps1`, but Windows may block local PowerShell scripts through Execution Policy. The `.cmd` helper avoids that issue.
