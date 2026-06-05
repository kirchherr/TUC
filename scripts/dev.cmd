@echo off
setlocal

set TASK=%1
if "%TASK%"=="" set TASK=shell

if "%TASK%"=="build" (
  docker compose build dev
  exit /b %ERRORLEVEL%
)

if "%TASK%"=="shell" (
  docker compose run --rm dev bash
  exit /b %ERRORLEVEL%
)

if "%TASK%"=="gpu-shell" (
  docker compose --profile gpu run --rm gpu bash
  exit /b %ERRORLEVEL%
)

if "%TASK%"=="pytest" (
  docker compose run --rm dev pytest -q
  exit /b %ERRORLEVEL%
)

if "%TASK%"=="check" (
  docker compose run --rm dev python -V || exit /b 1
  docker compose run --rm dev clang-18 --version || exit /b 1
  docker compose run --rm dev llvm-config-18 --version || exit /b 1
  docker compose run --rm dev mlir-opt-18 --version || exit /b 1
  docker compose run --rm dev python -c "import torch, triton, numpy; print('torch', torch.__version__, 'cuda', torch.cuda.is_available()); print('triton', triton.__version__); print('numpy', numpy.__version__)" || exit /b 1
  exit /b 0
)

echo Unknown task: %TASK%
echo Usage: scripts\dev.cmd [build^|shell^|gpu-shell^|check^|pytest]
exit /b 2
