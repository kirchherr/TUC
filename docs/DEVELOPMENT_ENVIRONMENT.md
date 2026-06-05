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
