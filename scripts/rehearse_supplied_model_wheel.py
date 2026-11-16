"""Rehearse the fixed supplied candidate wheel, without rebuilding TUC."""

from __future__ import annotations

import argparse
import json
import os
import platform
import stat
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

SOURCE = "fdfcc193b0b42405e3e48ea6ace1bdfbea066536"
CANDIDATE_RUN_ID = 43826307479
WHEEL_SHA256 = "db258c3ca5cb2861779ebdfbb6b2d6d6991d99ec27c1f40616a3f85d6a8ebf85"
WHEEL_NAME = "tuc-0.2.0-py3-none-any.whl"
LOCK = "requirements/research-release.txt"
LOCK_SHA256 = "88847096f470feeb70f9e14bd61d2e9a7ab6f1ebf48b4beb069d1be08f05ab1f"
CLIENT = "integration/bounded_model_application/"
AUDITOR = CLIENT + "audit_native_receipt.py"
CORE = CLIENT + "native_consumer.py"
SESSION = CLIENT + "native_session_consumer.py"
CLI = "integration/bounded_model_cli/"
FILES = (LOCK, AUDITOR, CORE, SESSION, *(CLI + p for p in (
    "consumer.py", "model.json", "backends.json", "inputs.json", "batch.json",
)))
RECORD_SHA256 = "6a77307516b633d45b45f8efa4581076c854549491960652026b7219a3ff8bd8"
MAX_WHEEL = 32 * 1024 * 1024
MAX_RECORD = 128 * 1024


class RehearsalRejected(ValueError):
    """A closed diagnostic that does not expose local paths or subprocess output."""


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
            .encode("ascii") + b"\n")


def read_regular(path: Path, limit: int) -> bytes:
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= limit:
        raise RehearsalRejected("file_boundary")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags | getattr(os, "O_NOFOLLOW", 0)), "rb") as stream:
        after = os.fstat(stream.fileno())
        if (not stat.S_ISREG(after.st_mode)
                or (before.st_dev, before.st_ino, before.st_size)
                != (after.st_dev, after.st_ino, after.st_size)):
            raise RehearsalRejected("file_boundary")
        data = stream.read(limit + 1)
    if len(data) != before.st_size:
        raise RehearsalRejected("file_boundary")
    return data


def supplied_wheel(path: Path) -> bytes:
    if path.name != WHEEL_NAME:
        raise RehearsalRejected("wheel_name")
    data = read_regular(path, MAX_WHEEL)
    if sha256(data).hexdigest() != WHEEL_SHA256:
        raise RehearsalRejected("wheel_digest")
    return data


def snapshot(repo: Path) -> dict[str, bytes]:
    # Fixed system Git and a finite blob list; no checkout hooks, attributes,
    # replace objects or working-tree Python files are executed or copied.
    git = Path("/usr/bin/git")
    if not git.is_file():
        raise RehearsalRejected("git_unavailable")
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "GIT_NO_REPLACE_OBJECTS": "1",
           "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    files = {}
    for name in FILES:
        result = subprocess.run(
            [str(git), "--no-pager", "--literal-pathspecs", "-c",
             f"safe.directory={repo.as_posix()}", "-C", str(repo),
             "cat-file", "blob", f"{SOURCE}:{name}"],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=15, check=True, env=env,
        )
        if not 0 < len(result.stdout) <= MAX_RECORD or result.stderr:
            raise RehearsalRejected("source_boundary")
        files[name] = result.stdout
    if sha256(files[LOCK]).hexdigest() != LOCK_SHA256:
        raise RehearsalRejected("lock_digest")
    return files


def output_directory(repo: Path, output: Path) -> Path:
    if not output.is_absolute() or ".." in output.parts or output.parent.is_symlink():
        raise RehearsalRejected("output_boundary")
    parent = output.parent.resolve(strict=True)
    if parent.is_relative_to(repo.resolve()) or output.exists() or output.is_symlink():
        raise RehearsalRejected("output_boundary")
    root = parent / output.name
    root.mkdir(mode=0o700)
    return root


def rehearse(repo: Path, wheel: Path, output: Path) -> dict[str, object]:
    if (platform.system() != "Linux" or platform.machine() != "x86_64"
            or sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 12)):
        raise RehearsalRejected("linux_x86_64_cpython_3_12_required")
    data = supplied_wheel(wheel)
    files = snapshot(repo)
    if not Path("/var/run/docker.sock").is_socket():
        raise RehearsalRejected("local_docker_socket_required")
    root = output_directory(repo, output)
    home, supply, run_env = (root / p for p in ("home", "supply", "run-env"))
    for directory in (home, supply):
        directory.mkdir(mode=0o700)
    (supply / WHEEL_NAME).write_bytes(data)
    (supply / "requirements.txt").write_bytes(files[LOCK])
    environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(home),
        "PIP_CONFIG_FILE": os.devnull, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        "LD_LIBRARY_PATH": str(Path(sys.base_prefix).resolve() / "lib")}
    completed = []

    def step(name: str, command: list[str], cwd: Path = root, timeout: int = 300) -> bytes:
        try:
            process = subprocess.run(command, cwd=cwd, env=environment,
                stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout, check=True)
        except (OSError, subprocess.SubprocessError):
            raise RehearsalRejected(name) from None
        if len(process.stdout) > 4 * 1024**2 or len(process.stderr) > 1024**2:
            raise RehearsalRejected("process_output_boundary")
        (root / (name + ".stdout.txt")).write_bytes(process.stdout)
        (root / (name + ".stderr.txt")).write_bytes(process.stderr)
        completed.append(name)
        return process.stdout

    server = json.loads(step("local_docker_version", ["/usr/bin/docker", "--host",
        "unix:///var/run/docker.sock", "version", "--format", "{{json .Server}}"], timeout=30))
    if server.get("Os") != "linux" or server.get("Arch") != "amd64":
        raise RehearsalRejected("docker_platform")
    cgroup = json.loads(step("local_docker_cgroup", ["/usr/bin/docker", "--host",
        "unix:///var/run/docker.sock", "info", "--format", "{{json .CgroupVersion}}"], timeout=30))
    if cgroup not in {"1", "2"}:
        raise RehearsalRejected("docker_cgroup")
    step("create_run_environment", [sys.executable, "-I", "-m", "venv", str(run_env)])
    python = str(run_env / "bin/python")
    pip = [python, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "--no-input"]
    step("install_locked_requirements", [*pip, "install", "--require-hashes",
        "--only-binary=:all:", "--no-cache-dir", "--index-url", "https://pypi.org/simple",
        "-r", str(supply / "requirements.txt")])
    step("install_supplied_wheel", [*pip, "install", "--no-deps", "--no-index",
        str(supply / WHEEL_NAME)])
    step("pip_check", [*pip, "check"])
    step("installed_origin", [python, "-I", "-c",
        "from pathlib import Path; import importlib.metadata,sys,tuc; "
        "assert importlib.metadata.version('tuc') == '0.2.0'; "
        "assert Path(tuc.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()); "
        "assert (Path(sys.prefix)/'bin/tuc-model-app').is_file(); "
        "assert not any(Path(p).resolve().is_relative_to(Path(sys.argv[1])) "
        "for p in sys.path if p); print('installed_origin=PASS')", str(repo.resolve())])
    audits = {}
    observations = {}
    for group, consumer in (("core", CORE), ("session", SESSION), ("cli", CLI + "consumer.py")):
        client = root / group
        client.mkdir(mode=0o700)
        names = (consumer, AUDITOR) if group != "cli" else (
            consumer, AUDITOR, *(CLI + p for p in (
                "model.json", "backends.json", "inputs.json", "batch.json",
            )))
        for name in names:
            (client / Path(name).name).write_bytes(files[name])
        entry = str(client / Path(consumer).name)
        step(group + "_candidate", [python, "-I", "-S", entry], cwd=client)
        flags = ["-I", "-S"] if group == "cli" else ["-I"]
        step(group + "_native", [python, *flags, entry, "--run"], cwd=client, timeout=2700)
        record_data = read_regular(client / "record.json", MAX_RECORD)
        record = json.loads(record_data)
        if (sha256(record_data).hexdigest() != RECORD_SHA256
                or record.get("native_execution_observed") is not True
                or record.get("workspaces_clean") is not True):
            raise RehearsalRejected("native_record")
        audit_data = step(group + "_audit", [python, "-I", "-S",
            str(client / "audit_native_receipt.py"), str(client / "record.json")], cwd=client)
        report = json.loads(audit_data)
        if (report.get("status") != "PASS" or report.get("scalar_checks") != 18
                or report.get("rejection_checks") != 4 or report.get("tuc_imported") is not False
                or report.get("native_execution_performed") is not False
                or report.get("record_sha256") != RECORD_SHA256):
            raise RehearsalRejected("numerical_audit")
        (client / "audit.json").write_bytes(audit_data)
        packet = {"integration": record, "audit": report, "source_commit": SOURCE,
            "wheel_sha256": WHEEL_SHA256, "consumer_sha256": sha256(files[consumer]).hexdigest(),
            "audit_sha256": sha256(files[AUDITOR]).hexdigest()}
        (client / "ci-record.json").write_bytes(encoded(packet))
        audits[group] = report
        if group != "core":
            observations[group] = json.loads(read_regular(
                client / (group + "-observation.json"), MAX_RECORD,
            ))
    session = observations["session"]
    if (session.get("status") != "PASS" or session.get("sessions") != 2
            or session.get("docker_builds") != 2 or session.get("native_runs") != 4
            or session.get("successful_runs") != 3 or session.get("sequences") != [1, 2, 1]
            or session.get("closed_session_rejections") != 1
            or session.get("workspaces_clean") is not True):
        raise RehearsalRejected("session_observation")
    cli = observations["cli"]
    if (cli.get("status") != "PASS" or cli.get("successful_requests") != 3
            or cli.get("batch_sequences") != [1, 2] or cli.get("single_sequence") != 1
            or cli.get("rejected_commands") != 7 or cli.get("workspaces_clean") is not True
            or cli.get("installed_outside_checkout") is not True):
        raise RehearsalRejected("cli_observation")
    result = {"schema_version": "tuc.supplied_model_candidate_rehearsal.v0", "status": "PASS",
        "source_commit": SOURCE, "candidate_run_id": CANDIDATE_RUN_ID,
        "supplied_wheel_sha256": WHEEL_SHA256,
        "requirements_sha256": LOCK_SHA256, "record_sha256": RECORD_SHA256,
        "procedure_sha256": sha256(read_regular(Path(__file__), MAX_RECORD)).hexdigest(),
        "source_material_sha256": {
            name: sha256(value).hexdigest() for name, value in files.items()},
        "completed_steps": completed, "audits": audits, "observations": observations,
        "environment": {"system": "Linux", "machine": "x86_64",
            "python": platform.python_version(), "docker_version": server["Version"],
            "docker_api_version": server["ApiVersion"], "docker_kernel": server["KernelVersion"],
            "docker_cgroup_version": cgroup},
        "tuc_wheel_rebuilt": False, "native_execution_observed": True,
        "external_origin_verified": False, "independent_operator_acceptance": False}
    (root / "rehearsal.json").write_bytes(encoded(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = rehearse(Path(__file__).resolve().parents[1], args.wheel, args.output)
    except RehearsalRejected as error:
        print(f"supplied_model_wheel_rejected:{error}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError, RecursionError, subprocess.SubprocessError):
        print("supplied_model_wheel_rejected", file=sys.stderr)
        return 2
    print(encoded(result).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
