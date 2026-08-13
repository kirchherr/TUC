"""Verify Objective Delta against an installed wheel outside the source tree."""

from __future__ import annotations

import argparse
import hashlib
import shutil
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

MAX_OBJECTIVE_DELTA_CONSUMER_FILES = 16
MAX_OBJECTIVE_DELTA_CONSUMER_BYTES = 256 * 1024
OBJECTIVE_DELTA_CONSUMER_SHA256 = (
    "ca19318cf656bcbb895633ab26afcc6efcb6edd6cef12ad0a05bec3f0a8a9539"
)
OBJECTIVE_DELTA_CONSUMER_FILES = frozenset(
    {
        "README.md",
        "consumer.py",
        "expected_report.json",
        "external_systolic.v0.json",
        "external_vector.v0.json",
        "source_intent.v0.json",
    }
)


def verify_external_portable_compute_consumer(
    *,
    wheel_path: Path,
    consumer_source: Path,
    source_root: Path,
) -> None:
    """Install a wheel and replay Objective Delta through public API and CLI."""

    wheel = _resolve_regular_file(wheel_path, "wheel")
    consumer = _resolve_directory(consumer_source, "consumer source")
    source = _resolve_directory(source_root, "source root")
    if wheel.suffix != ".whl":
        raise ValueError("wheel must use the .whl suffix")
    _validate_consumer_tree(consumer)

    with tempfile.TemporaryDirectory(prefix="tuc-objective-delta-") as temporary:
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
        verifier = _environment_command(
            environment_root,
            "tuc-prove-portable-compute",
        )
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
            [
                str(verifier),
                str(consumer_root / "source_intent.v0.json"),
                str(consumer_root / "external_systolic.v0.json"),
                str(consumer_root / "external_vector.v0.json"),
            ],
            cwd=temporary_root,
        )
        if api_result.stdout != expected:
            raise RuntimeError("installed portable-compute API report mismatch")
        if cli_result.stdout != expected:
            raise RuntimeError("installed portable-compute CLI report mismatch")


def _validate_consumer_tree(consumer_root: Path) -> None:
    entries = tuple(consumer_root.rglob("*"))
    if len(entries) > MAX_OBJECTIVE_DELTA_CONSUMER_FILES:
        raise ValueError("portable-compute consumer exceeds file-count limit")
    observed_files: set[str] = set()
    total_bytes = 0
    for entry in entries:
        if entry.is_symlink():
            raise ValueError("portable-compute consumer must not contain symlinks")
        if entry.is_dir():
            continue
        if not entry.is_file():
            raise ValueError("portable-compute consumer entry must be regular file")
        total_bytes += entry.stat().st_size
        observed_files.add(entry.relative_to(consumer_root).as_posix())
    if total_bytes > MAX_OBJECTIVE_DELTA_CONSUMER_BYTES:
        raise ValueError("portable-compute consumer exceeds byte limit")
    if observed_files != OBJECTIVE_DELTA_CONSUMER_FILES:
        raise ValueError("portable-compute consumer file set changed")
    consumer_digest = hashlib.sha256((consumer_root / "consumer.py").read_bytes()).hexdigest()
    if consumer_digest != OBJECTIVE_DELTA_CONSUMER_SHA256:
        raise ValueError("portable-compute consumer source digest mismatch")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--consumer", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    verify_external_portable_compute_consumer(
        wheel_path=args.wheel,
        consumer_source=args.consumer,
        source_root=args.source_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
