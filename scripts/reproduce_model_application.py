"""Run the fixed native model probe or review a returned data-only observation."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import stat
import subprocess
import sys
import tempfile
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "tuc.bounded_model_application_operator_observation.v0"
MAX_PACKET = 128 * 1024
MAX_SOURCE = 16 * 1024 * 1024
MAX_WHEEL = 32 * 1024 * 1024
TRUSTED_PATH = "/usr/local/bin:/usr/bin:/bin"
LOCK = "requirements/ci.txt"
CLIENT = "integration/bounded_model_application/"
CONSUMER = CLIENT + "native_consumer.py"
AUDITOR = CLIENT + "audit_native_receipt.py"
IDENTITY_FILES = (LOCK, CONSUMER, AUDITOR)
BUILD_FILES = (*IDENTITY_FILES, "pyproject.toml", "README.md", "LICENSE", "NOTICE")
STEPS = (
    "snapshot", "create_build_env", "download_locked_wheels", "install_build_requirements",
    "build_wheel", "create_run_env", "install_run_requirements", "install_wheel",
    "check_installed_origin", "candidate", "native_run", "stdlib_audit",
)
COMMIT = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
SAFE_PATH = re.compile(r"[a-zA-Z0-9_./-]+")


class ReproductionRejected(ValueError):
    """A fixed failure reason safe to print in CI or a public report."""


def encoded(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
        + b"\n"
    )


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _read(path: Path, limit: int = MAX_PACKET) -> bytes:
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= limit:
        raise ReproductionRejected("file_boundary")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags | getattr(os, "O_NOFOLLOW", 0)), "rb") as stream:
        after = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(after.st_mode)
            or (before.st_dev, before.st_ino, before.st_size)
            != (after.st_dev, after.st_ino, after.st_size)
        ):
            raise ReproductionRejected("file_boundary")
        data = stream.read(limit + 1)
    if len(data) != before.st_size:
        raise ReproductionRejected("file_boundary")
    return data


def _git_executable(repo: Path) -> str:
    name = "git.exe" if os.name == "nt" else "git"
    for entry in os.get_exec_path():
        directory = Path(entry)
        if not directory.is_absolute():
            continue
        try:
            directory = directory.resolve(strict=True)
            candidate = (directory / name).resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if (
            not directory.is_relative_to(repo) and not candidate.is_relative_to(repo)
            and candidate.is_file() and os.access(candidate, os.X_OK)
        ):
            return str(candidate)
    raise ReproductionRejected("git_unavailable")


def _git(repo: Path, *args: str) -> bytes:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update(GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    return subprocess.run(
        [_git_executable(repo), "--no-pager", "--literal-pathspecs",
         "-c", f"safe.directory={repo.as_posix()}", "-C", str(repo), *args],
        env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        timeout=15, check=True,
    ).stdout


def _snapshot(repo: Path, commit: str, *, build: bool) -> dict[str, bytes]:
    if COMMIT.fullmatch(commit) is None or _git(repo, "rev-parse", "--verify", "HEAD").strip() != (
        commit.encode("ascii")
    ):
        raise ReproductionRejected("source_revision")
    fixed = BUILD_FILES if build else IDENTITY_FILES
    paths = (*fixed, "src/tuc") if build else fixed
    listing = _git(repo, "ls-tree", "-r", "-l", "-z", commit, "--", *paths)
    if len(listing) > MAX_PACKET:
        raise ReproductionRejected("source_budget")
    entries: dict[str, tuple[str, int]] = {}
    size_total = 0
    for line in listing.split(b"\0"):
        if not line:
            continue
        metadata, raw_path = line.split(b"\t", 1)
        mode, kind, raw_oid, size = metadata.decode("ascii").split()
        name = raw_path.decode("ascii")
        if (
            mode not in {"100644", "100755"} or kind != "blob"
            or COMMIT.fullmatch(raw_oid) is None or SAFE_PATH.fullmatch(name) is None
            or any(part in {"", ".", ".."} for part in name.split("/"))
            or name in entries or not (name in fixed or (build and name.startswith("src/tuc/")))
        ):
            raise ReproductionRejected("source_file_type")
        length = int(size)
        size_total += length
        if length < 0 or size_total > MAX_SOURCE or len(entries) >= 1024:
            raise ReproductionRejected("source_budget")
        entries[name] = (raw_oid, length)
    if not set(fixed).issubset(entries) or (build and "src/tuc/__init__.py" not in entries):
        raise ReproductionRejected("source_missing")
    files = {}
    for name, (oid, length) in entries.items():
        data = _git(repo, "cat-file", "blob", oid)
        if len(data) != length:
            raise ReproductionRejected("source_size")
        files[name] = data
    return files


def _checked(
    args: list[str], *, cwd: Path, env: dict[str, str], timeout: int, capture: bool = False,
) -> bytes:
    return subprocess.run(
        args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=timeout, check=True,
    ).stdout or b""


def _python_environment() -> dict[str, str]:
    # setup-python's Linux interpreter can require its own shared library.
    # Derive that location instead of inheriting loader overrides.
    if sys.platform == "linux":
        return {"LD_LIBRARY_PATH": str(Path(sys.base_prefix).resolve() / "lib")}
    if os.name == "nt" and "SYSTEMROOT" in os.environ:
        return {"SYSTEMROOT": os.environ["SYSTEMROOT"]}
    return {}


def _audit(auditor: Path, record: Path, *, ci_packet: bool = False) -> dict[str, Any]:
    args = [sys.executable, "-I", "-S", str(auditor)]
    if ci_packet:
        args.append("--ci-packet")
    args.append(str(record))
    result = _checked(args, cwd=auditor.parent, env=_python_environment(),
                      timeout=30, capture=True)
    report = json.loads(result)
    if (
        not isinstance(report, dict) or report.get("status") != "PASS"
        or report.get("scalar_checks") != 18 or report.get("rejection_checks") != 4
        or report.get("tuc_imported") is not False
        or report.get("native_execution_performed") is not False
    ):
        raise ReproductionRejected("audit_result")
    return report


def verify(
    data: bytes, *, commit: str, files: dict[str, bytes], expected_wheel: str | None = None,
) -> dict[str, object]:
    """Check bindings and arithmetic; claimed origin is deliberately unassessed."""
    if not 0 < len(data) <= MAX_PACKET:
        raise ReproductionRejected("packet_budget")
    value = json.loads(data)
    if (
        type(value) is not dict or set(value) != {
            "schema_version", "packet", "environment", "completed_steps",
            "requirements_sha256", "external_origin_verified",
        }
        or encoded(value) != data or value["schema_version"] != SCHEMA
        or value["external_origin_verified"] is not False
        or value["completed_steps"] != list(STEPS)
        or value["requirements_sha256"] != _digest(files[LOCK])
    ):
        raise ReproductionRejected("packet_shape")
    env = value["environment"]
    if (
        type(env) is not dict or set(env) != {"system", "machine", "python"}
        or env["system"] != "Linux" or env["machine"] != "x86_64"
        or type(env["python"]) is not str
        or re.fullmatch(r"3\.12\.[0-9]{1,3}", env["python"]) is None
    ):
        raise ReproductionRejected("environment_claim")
    packet = value["packet"]
    if (
        type(packet) is not dict or packet.get("source_commit") != commit
        or packet.get("consumer_sha256") != _digest(files[CONSUMER])
        or packet.get("audit_sha256") != _digest(files[AUDITOR])
        or type(packet.get("wheel_sha256")) is not str
        or DIGEST.fullmatch(packet["wheel_sha256"]) is None
        or (expected_wheel is not None and packet["wheel_sha256"] != expected_wheel)
    ):
        raise ReproductionRejected("packet_binding")
    with tempfile.TemporaryDirectory(prefix="tuc-model-review-") as directory:
        root = Path(directory)
        auditor, receipt = root / "audit_native_receipt.py", root / "ci-record.json"
        auditor.write_bytes(files[AUDITOR])
        receipt.write_bytes(encoded(packet))
        try:
            report = _audit(auditor, receipt, ci_packet=True)
        except subprocess.SubprocessError:
            raise ReproductionRejected("packet_audit") from None
    return {
        "status": "PASS", "source_commit": commit, "wheel_sha256": packet["wheel_sha256"],
        "record_sha256": report["record_sha256"], "scalar_checks": 18, "rejection_checks": 4,
        "external_origin_verified": False, "native_execution_performed": False,
    }


def _output(repo: Path, output: Path) -> Path:
    if ".." in output.parts or output.name in {"", "."} or output.parent.is_symlink():
        raise ReproductionRejected("output_boundary")
    parent = output.parent.resolve(strict=True)
    if parent.is_relative_to(repo):
        raise ReproductionRejected("output_boundary")
    root = parent / output.name
    root.mkdir(mode=0o700)
    return root


def reproduce(repo: Path, commit: str, output: Path) -> dict[str, object]:
    if (
        platform.system() != "Linux" or platform.machine() != "x86_64"
        or sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 12)
    ):
        raise ReproductionRejected("linux_x86_64_cpython_3_12_required")
    if not Path("/var/run/docker.sock").is_socket():
        raise ReproductionRejected("local_docker_socket_required")
    files = _snapshot(repo, commit, build=True)
    root = _output(repo, output)
    source, deps, wheels, client, home = (root / name for name in (
        "source", "dependencies", "wheels", "client", "home",
    ))
    for path in (source, deps, wheels, client, home):
        path.mkdir(mode=0o700)
    for name, data in files.items():
        path = source.joinpath(*PurePosixPath(name).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    completed = ["snapshot"]
    env = {**_python_environment(), "PATH": TRUSTED_PATH, "HOME": str(home),
           "PIP_CONFIG_FILE": os.devnull,
           "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}

    def step(name: str, args: list[str], *, cwd: Path = root, timeout: int = 180) -> None:
        try:
            _checked(args, cwd=cwd, env=env, timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            raise ReproductionRejected(name) from None
        completed.append(name)

    build_env, run_env = root / "build-env", root / "run-env"
    build_python, run_python = (str(p / "bin/python") for p in (build_env, run_env))
    pip = ["-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "--no-input"]
    lock = ["--require-hashes", "-r", str(source / LOCK)]
    local = ["--no-index", "--find-links", str(deps)]
    step("create_build_env", [sys.executable, "-I", "-m", "venv", str(build_env)])
    step("download_locked_wheels", [
        build_python, *pip, "download", "--no-cache-dir", "--only-binary=:all:",
        "--index-url", "https://pypi.org/simple", "--dest", str(deps), *lock,
    ], timeout=300)
    step("install_build_requirements", [build_python, *pip, "install", *local, *lock])
    step("build_wheel", [
        build_python, *pip, "wheel", "--no-deps", "--no-build-isolation", "--no-index",
        str(source), "--wheel-dir", str(wheels),
    ])
    built = list(wheels.glob("tuc-*-py3-none-any.whl"))
    if len(built) != 1 or len(list(wheels.iterdir())) != 1:
        raise ReproductionRejected("wheel_boundary")
    wheel = built[0]
    wheel_sha = _digest(_read(wheel, MAX_WHEEL))
    step("create_run_env", [sys.executable, "-I", "-m", "venv", str(run_env)])
    step("install_run_requirements", [run_python, *pip, "install", *local, *lock])
    step("install_wheel", [run_python, *pip, "install", "--no-deps", "--no-index", str(wheel)])
    step("check_installed_origin", [run_python, "-I", "-c",
         "from pathlib import Path; import sys,tuc; "
         "assert Path(tuc.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()); "
         "assert not any(Path(p).resolve().is_relative_to(Path(sys.argv[1])) "
         "for p in sys.path if p)", str(source)], cwd=client)
    consumer, auditor = client / "native_consumer.py", client / "audit_native_receipt.py"
    consumer.write_bytes(files[CONSUMER])
    auditor.write_bytes(files[AUDITOR])
    step("candidate", [run_python, "-I", str(consumer)], cwd=client)
    step("native_run", [run_python, "-I", str(consumer), "--run"], cwd=client, timeout=2700)
    record = client / "record.json"
    integration = json.loads(_read(record))
    report = _audit(auditor, record)
    completed.append("stdlib_audit")
    packet = {
        "integration": integration, "audit": report, "source_commit": commit,
        "wheel_sha256": wheel_sha, "consumer_sha256": _digest(files[CONSUMER]),
        "audit_sha256": _digest(files[AUDITOR]),
    }
    data = encoded({
        "schema_version": SCHEMA, "packet": packet, "completed_steps": completed,
        "environment": {"system": "Linux", "machine": "x86_64",
                        "python": platform.python_version()},
        "requirements_sha256": _digest(files[LOCK]), "external_origin_verified": False,
    })
    result = verify(data, commit=commit, files=files, expected_wheel=wheel_sha)
    (root / "ci-record.json").write_bytes(encoded(packet))
    with (root / "operator-observation.json").open("xb") as stream:
        stream.write(data)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run, review = sub.add_parser("run"), sub.add_parser("verify")
    for command in (run, review):
        command.add_argument("--source-commit", required=True)
    run.add_argument("--output", required=True, type=Path)
    review.add_argument("observation", type=Path)
    review.add_argument("--expected-wheel-sha256")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    try:
        if args.command == "run":
            result = reproduce(repo, args.source_commit, args.output)
        else:
            files = _snapshot(repo, args.source_commit, build=False)
            result = verify(_read(args.observation), commit=args.source_commit, files=files,
                            expected_wheel=args.expected_wheel_sha256)
    except ReproductionRejected as error:
        print(f"model_application_reproduction_rejected:{error}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError, RecursionError, subprocess.SubprocessError):
        print("model_application_reproduction_rejected", file=sys.stderr)
        return 2
    print(encoded(result).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
