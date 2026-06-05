[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("build", "shell", "gpu-shell", "check", "pytest")]
    [string] $Task = "shell"
)

$ErrorActionPreference = "Stop"

function Invoke-Compose {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]] $ComposeArgs
    )

    & docker compose @ComposeArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

switch ($Task) {
    "build" {
        Invoke-Compose build dev
    }
    "shell" {
        Invoke-Compose run --rm dev bash
    }
    "gpu-shell" {
        Invoke-Compose --profile gpu run --rm gpu bash
    }
    "check" {
        $checkCommand = @'
set -e
python -V
clang-18 --version | head -n 1
llvm-config-18 --version
mlir-opt-18 --version | head -n 1
python -c "import torch, triton, numpy; print('torch', torch.__version__, 'cuda', torch.cuda.is_available()); print('triton', triton.__version__); print('numpy', numpy.__version__)"
'@
        Invoke-Compose run --rm dev bash -lc $checkCommand
    }
    "pytest" {
        Invoke-Compose run --rm dev pytest -q
    }
}
