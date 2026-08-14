"""Verify Objective Delta reproduction against an installed wheel."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
import venv
from pathlib import Path

from verify_external_backend_consumer import (
    _assert_installed_package_is_outside_source,
    _environment_command,
    _expose_locked_runtime_dependencies,
    _isolated_environment,
    _resolve_directory,
    _resolve_regular_file,
    _run_checked,
)

MAX_EXPECTED_RECEIPT_BYTES = 64 * 1024
MAX_REPRODUCTION_KIT_BYTES = 256 * 1024


def verify_external_portable_compute_reproduction(
    *,
    wheel_path: Path,
    kit_path: Path,
    expected_receipt_path: Path,
    source_root: Path,
) -> None:
    """Install one wheel and reproduce Objective Delta outside its source tree."""

    wheel = _resolve_regular_file(wheel_path, "wheel")
    kit = _resolve_regular_file(kit_path, "reproduction kit")
    expected_receipt = _resolve_regular_file(expected_receipt_path, "expected receipt")
    source = _resolve_directory(source_root, "source root")
    if wheel.suffix != ".whl":
        raise ValueError("wheel must use the .whl suffix")
    if kit.suffix != ".zip" or kit.stat().st_size > MAX_REPRODUCTION_KIT_BYTES:
        raise ValueError("reproduction kit boundary invalid")
    if (
        expected_receipt.suffix != ".json"
        or expected_receipt.stat().st_size > MAX_EXPECTED_RECEIPT_BYTES
    ):
        raise ValueError("expected receipt boundary invalid")

    with tempfile.TemporaryDirectory(prefix="tuc-objective-delta-reproduction-") as root:
        temporary = Path(root)
        environment_root = temporary / "environment"
        venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment_root)
        _expose_locked_runtime_dependencies(environment_root)
        python = _environment_command(environment_root, "python")
        subprocess.run(
            [
                str(python),
                "-I",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--force-reinstall",
                "--no-deps",
                str(wheel),
            ],
            check=True,
            cwd=temporary,
            env=_isolated_environment(),
            stdout=subprocess.DEVNULL,
            timeout=120,
        )
        _assert_installed_package_is_outside_source(
            python=python,
            source_root=source,
            cwd=temporary,
        )
        command = _environment_command(environment_root, "tuc-reproduce-portable-compute")
        completed = _run_checked([str(command), str(kit)], cwd=temporary)
        if completed.stdout != expected_receipt.read_bytes():
            raise RuntimeError("installed portable-compute reproduction receipt mismatch")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--expected-receipt", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    verify_external_portable_compute_reproduction(
        wheel_path=args.wheel,
        kit_path=args.kit,
        expected_receipt_path=args.expected_receipt,
        source_root=args.source_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
