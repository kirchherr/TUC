"""Verify Objective Gamma against an installed wheel outside the source tree."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

import numpy as np

MAX_EXTERNAL_CONSUMER_FILES = 16
MAX_EXTERNAL_CONSUMER_BYTES = 256 * 1024
OBJECTIVE_GAMMA_CONSUMER_SHA256 = (
    "cbd9b092254daf9cf5ca372e79c81a6467fa98051afa85a214a292fff74e367a"
)
OBJECTIVE_GAMMA_CONSUMER_FILES = frozenset(
    {
        "README.md",
        "backend_package.v0.json",
        "consumer.py",
        "expected_report.json",
    }
)


def verify_external_consumer(
    *,
    wheel_path: Path,
    consumer_source: Path,
    source_root: Path,
) -> None:
    """Install a wheel and run the copied consumer through API and CLI paths."""

    wheel = _resolve_regular_file(wheel_path, "wheel")
    consumer = _resolve_directory(consumer_source, "consumer source")
    source = _resolve_directory(source_root, "source root")
    if wheel.suffix != ".whl":
        raise ValueError("wheel must use the .whl suffix")
    _validate_consumer_tree(consumer)

    with tempfile.TemporaryDirectory(prefix="tuc-objective-gamma-") as temporary:
        temporary_root = Path(temporary)
        environment_root = temporary_root / "environment"
        consumer_root = temporary_root / "consumer"
        venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment_root)
        _expose_locked_runtime_dependencies(environment_root)
        shutil.copytree(consumer, consumer_root)

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
            cwd=temporary_root,
            env=_isolated_environment(),
            stdout=subprocess.DEVNULL,
            timeout=120,
        )
        verifier = _environment_command(environment_root, "tuc-backend-verify")
        _assert_installed_package_is_outside_source(
            python=python,
            source_root=source,
            cwd=temporary_root,
        )

        expected = (consumer_root / "expected_report.json").read_bytes()
        api_result = _run_checked(
            [str(python), "-I", str(consumer_root / "consumer.py")],
            cwd=temporary_root,
        )
        cli_result = _run_checked(
            [str(verifier), str(consumer_root / "backend_package.v0.json")],
            cwd=temporary_root,
        )
        if api_result.stdout != expected:
            raise RuntimeError("installed-wheel API consumer report mismatch")
        if cli_result.stdout != expected:
            raise RuntimeError("installed-wheel CLI consumer report mismatch")


def _assert_installed_package_is_outside_source(
    *, python: Path, source_root: Path, cwd: Path
) -> None:
    check = (
        "from pathlib import Path; import sys, tuc; "
        "installed=Path(tuc.__file__).resolve(); source=Path(sys.argv[1]).resolve(); "
        "raise SystemExit(1 if installed.is_relative_to(source) else 0)"
    )
    _run_checked([str(python), "-I", "-c", check, str(source_root)], cwd=cwd)


def _run_checked(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        check=True,
        cwd=cwd,
        env=_isolated_environment(),
        capture_output=True,
        timeout=60,
    )


def _isolated_environment() -> dict[str, str]:
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    return environment


def _expose_locked_runtime_dependencies(environment_root: Path) -> None:
    numpy_file = np.__file__
    if numpy_file is None:
        raise RuntimeError("NumPy installation path is unavailable")
    dependency_site = Path(numpy_file).resolve(strict=True).parents[1]
    if "\n" in str(dependency_site) or "\r" in str(dependency_site):
        raise RuntimeError("runtime dependency path is invalid")
    if os.name == "nt":
        environment_site = environment_root / "Lib" / "site-packages"
    else:
        version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        environment_site = environment_root / "lib" / version / "site-packages"
    if not environment_site.is_dir() or environment_site.is_symlink():
        raise RuntimeError("isolated environment site-packages is unavailable")
    (environment_site / "tuc-locked-runtime-dependencies.pth").write_text(
        f"{dependency_site}\n",
        encoding="utf-8",
    )


def _environment_command(environment_root: Path, command: str) -> Path:
    if os.name == "nt":
        path = environment_root / "Scripts" / f"{command}.exe"
    else:
        path = environment_root / "bin" / command
    _require_regular_file(path, command)
    return path


def _resolve_regular_file(path: Path, label: str) -> Path:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    resolved = path.resolve(strict=True)
    _require_regular_file(resolved, label)
    return resolved


def _resolve_directory(path: Path, label: str) -> Path:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    resolved = path.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError(f"{label} must be a directory")
    return resolved


def _require_regular_file(path: Path, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be a regular non-symlink file")


def _validate_consumer_tree(consumer_root: Path) -> None:
    entries = tuple(consumer_root.rglob("*"))
    if len(entries) > MAX_EXTERNAL_CONSUMER_FILES:
        raise ValueError("consumer source exceeds file-count limit")
    total_bytes = 0
    observed_files: set[str] = set()
    for entry in entries:
        if entry.is_symlink():
            raise ValueError("consumer source must not contain symlinks")
        if entry.is_dir():
            continue
        _require_regular_file(entry, "consumer entry")
        total_bytes += entry.stat().st_size
        observed_files.add(entry.relative_to(consumer_root).as_posix())
    if total_bytes > MAX_EXTERNAL_CONSUMER_BYTES:
        raise ValueError("consumer source exceeds byte limit")
    if observed_files != OBJECTIVE_GAMMA_CONSUMER_FILES:
        raise ValueError("consumer source file set changed")
    consumer_digest = hashlib.sha256((consumer_root / "consumer.py").read_bytes()).hexdigest()
    if consumer_digest != OBJECTIVE_GAMMA_CONSUMER_SHA256:
        raise ValueError("consumer source digest mismatch")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    verify_external_consumer(
        wheel_path=args.wheel,
        consumer_source=args.consumer,
        source_root=args.source_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
