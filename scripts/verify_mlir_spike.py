"""Verify the TUC MLIR design-spike artifact with mlir-opt."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_INPUT = _REPO_ROOT / "examples" / "mlir" / "tuc_hac_ir_spike.mlir"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=_DEFAULT_INPUT)
    parser.add_argument("--mlir-opt", default="mlir-opt")
    args = parser.parse_args(argv)

    source = args.input.resolve()
    if source != _DEFAULT_INPUT.resolve():
        print("verification input must be the repository MLIR spike artifact", file=sys.stderr)
        return 2
    if not source.is_file():
        print(f"MLIR spike artifact is missing: {source}", file=sys.stderr)
        return 2

    command = [args.mlir_opt, "--allow-unregistered-dialect", str(source)]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"failed to run mlir-opt: {exc}", file=sys.stderr)
        return 2

    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, end="")
        return result.returncode

    print("MLIR spike artifact parsed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
