"""Offline consistency audit of the fixed supplied-wheel observation packet.

Only the digest-pinned, repository-owned stdlib numerical auditor is executed.
Returned JSON never grants execution authority or authenticates its producer.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any

SOURCE = "fdfcc193b0b42405e3e48ea6ace1bdfbea066536"
WHEEL = "db258c3ca5cb2861779ebdfbb6b2d6d6991d99ec27c1f40616a3f85d6a8ebf85"
PROCEDURE = "78a1e585b4d3f7cae3504bad607f9aea75445941fdd70305b22a280652c58f78"
RECORD = "6a77307516b633d45b45f8efa4581076c854549491960652026b7219a3ff8bd8"
APP = "integration/bounded_model_application/"
CLI = "integration/bounded_model_cli/"
AUDITOR = APP + "audit_native_receipt.py"
MATERIALS = {
    AUDITOR: "aedef34c29ac211415595f39fbb1ecb47b3690cc9b5c6b51a9b4c603d020f231",
    APP + "native_consumer.py":
        "f4918725c7dfcb1a49d3c75132e94a843a0bc035fa0ee33d208193320b9c5c77",
    APP + "native_session_consumer.py":
        "0254e07faa7a4eddde39a08ae0615c3899d6b6a3d712e9788623f83441171582",
    CLI + "consumer.py": "4129d39900c3d172c3d61e17c84db33aad41282547224e8400c598304039bdda",
    CLI + "model.json": "c958d1c9ee7aee8d0615a418426f8f6622109d27fd20ae2754951c0d162a489f",
    CLI + "backends.json": "53cff8eee56d82e7cc5add73846a81e1b57c926d8b6db7977347831e4bf1f261",
    CLI + "inputs.json": "30f5090ff75019d1c42f0f983e0cf69055ea2008b97c3da9fe4c2c01f9f86faa",
    CLI + "batch.json": "b1046707af564747d83616ed11b66a3d3e28b42959b7bcb9140d555678efc863",
    "requirements/research-release.txt":
        "88847096f470feeb70f9e14bd61d2e9a7ab6f1ebf48b4beb069d1be08f05ab1f",
}
CONSUMERS = {"core": APP + "native_consumer.py",
             "session": APP + "native_session_consumer.py", "cli": CLI + "consumer.py"}
FILES = ("rehearsal.json", *(f"{g}/{n}.json" for g in CONSUMERS
                           for n in ("record", "audit", "ci-record")),
         "session/session-observation.json", "cli/cli-observation.json")
STEPS = ["local_docker_version", "local_docker_cgroup", "create_run_environment",
         "install_locked_requirements", "install_supplied_wheel", "pip_check", "installed_origin",
         *(f"{g}_{s}" for g in CONSUMERS for s in ("candidate", "native", "audit"))]
SESSION = {"schema_version": "tuc.bounded_model_application_session_observation.v0",
           "status": "PASS", "sessions": 2, "docker_builds": 2, "native_runs": 4,
           "successful_runs": 3, "sequences": [1, 2, 1], "closed_session_rejections": 1,
           "workspaces_clean": True, "native_execution_observed": True, "record_sha256": RECORD}
CLI_OBSERVATION = {"schema_version": "tuc.bounded_model_cli_observation.v0", "status": "PASS",
                   "successful_requests": 3, "rejected_commands": 7, "batch_sequences": [1, 2],
                   "single_sequence": 1, "workspaces_clean": True,
                   "installed_outside_checkout": True, "native_execution_observed": True}
MAX_BYTES = 128 * 1024
TRUSTED_AUDITOR = Path(__file__).resolve().parents[1] / AUDITOR


class PacketRejected(ValueError):
    """A bounded data or fixed identity check failed."""


def encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(",", ":")).encode("ascii") + b"\n"


def require_equal(actual: object, expected: object) -> None:
    # JSON equality must distinguish a boolean from the integers 0 and 1.
    if encoded(actual) != encoded(expected):
        raise PacketRejected("packet_binding")


def read_regular(path: Path) -> bytes:
    """Reject redirects and special files before a nonblocking descriptor read."""
    path = Path(os.path.abspath(path))
    try:
        for parent in (*reversed(path.parents), path):
            info = parent.lstat()
            if (stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400):
                raise PacketRejected("file_boundary")
            if parent != path and not stat.S_ISDIR(info.st_mode):
                raise PacketRejected("file_boundary")
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_BYTES:
            raise PacketRejected("file_boundary")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        flags |= getattr(os, "O_BINARY", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode)
                    or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)
                    or not 0 < opened.st_size <= MAX_BYTES):
                raise PacketRejected("file_boundary")
            data = stream.read(MAX_BYTES + 1)
        if not 0 < len(data) <= MAX_BYTES:
            raise PacketRejected("file_boundary")
        return data
    except OSError:
        raise PacketRejected("file_boundary") from None


def read_json(data: bytes) -> dict[str, Any]:
    if type(data) is not bytes or not 0 < len(data) <= MAX_BYTES:
        raise PacketRejected("json_boundary")
    try:
        text = data.decode("ascii")
        depth, quoted, escape = 0, False, False
        for char in text:
            if quoted:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                depth += 1
                if depth > 12:
                    raise PacketRejected("json_boundary")
            elif char in "]}":
                depth -= 1

        def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
            result = {}
            for key, value in items:
                if key in result:
                    raise PacketRejected("json_boundary")
                result[key] = value
            return result

        def integer(value: str) -> int:
            if len(value) > 15:
                raise PacketRejected("json_boundary")
            return int(value)

        def forbidden(value: str) -> None:
            raise PacketRejected("json_boundary")

        result: dict[str, Any] = json.loads(
            text, object_pairs_hook=pairs, parse_int=integer,
            parse_float=forbidden, parse_constant=forbidden,
        )
        if type(result) is not dict:
            raise PacketRejected("json_boundary")
        return result
    except (ValueError, UnicodeError, RecursionError):
        raise PacketRejected("json_boundary") from None


def audit(directory: Path) -> dict[str, Any]:
    """Snapshot twelve fixed data files, validate claims, then rerun arithmetic."""
    data = {name: read_regular(directory / name) for name in FILES}
    records = {name: read_json(value) for name, value in data.items()}
    envelope = records["rehearsal.json"]
    audits = {}
    for group, consumer in CONSUMERS.items():
        raw = data[f"{group}/record.json"]
        if sha256(raw).hexdigest() != RECORD:
            raise PacketRejected("record_digest")
        report = records[f"{group}/audit.json"]
        require_equal(records[f"{group}/ci-record.json"], {
            "integration": records[f"{group}/record.json"], "audit": report,
            "source_commit": SOURCE, "wheel_sha256": WHEEL,
            "consumer_sha256": MATERIALS[consumer], "audit_sha256": MATERIALS[AUDITOR],
        })
        audits[group] = report
    require_equal(records["session/session-observation.json"], SESSION)
    require_equal(records["cli/cli-observation.json"], CLI_OBSERVATION)
    environment = envelope.get("environment")
    if type(environment) is not dict or set(environment) != {
        "system", "machine", "python", "docker_version", "docker_api_version",
        "docker_kernel", "docker_cgroup_version",
    }:
        raise PacketRejected("environment_claim")
    if any(type(value) is not str or not 0 < len(value) <= 256
           or not value.isascii() or not value.isprintable() for value in environment.values()):
        raise PacketRejected("environment_claim")
    if (environment["system"] != "Linux" or environment["machine"] != "x86_64"
            or environment["docker_cgroup_version"] != "2"
            or not re.fullmatch(r"3\.12\.[0-9]{1,3}", environment["python"])):
        raise PacketRejected("environment_claim")
    require_equal(envelope, {
        "schema_version": "tuc.supplied_model_candidate_rehearsal.v0", "status": "PASS",
        "source_commit": SOURCE, "candidate_run_id": 43826307479,
        "supplied_wheel_sha256": WHEEL, "requirements_sha256": MATERIALS[
            "requirements/research-release.txt"], "record_sha256": RECORD,
        "procedure_sha256": PROCEDURE, "source_material_sha256": MATERIALS,
        "completed_steps": STEPS, "audits": audits,
        "observations": {"session": SESSION, "cli": CLI_OBSERVATION},
        "environment": environment, "tuc_wheel_rebuilt": False,
        "native_execution_observed": True, "external_origin_verified": False,
        "independent_operator_acceptance": False,
    })
    auditor = read_regular(TRUSTED_AUDITOR)
    if sha256(auditor).hexdigest() != MATERIALS[AUDITOR]:
        raise PacketRejected("trusted_auditor_digest")
    # The returned directory supplies data only; it cannot select executable code.
    with tempfile.TemporaryDirectory(prefix="tuc-offline-model-audit-") as scratch:
        root = Path(scratch)
        script = root / "audit_native_receipt.py"
        script.write_bytes(auditor)
        environment = {"PATH": os.defpath}
        if os.name == "nt" and "SYSTEMROOT" in os.environ:
            environment["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
        for group in CONSUMERS:
            packet = root / (group + ".json")
            packet.write_bytes(data[f"{group}/ci-record.json"])
            try:
                result = subprocess.run(
                    [sys.executable, "-I", "-S", str(script), str(packet), "--ci-packet"],
                    cwd=root, env=environment, stdin=subprocess.DEVNULL,
                    capture_output=True, check=True, timeout=15,
                )
            except (OSError, subprocess.SubprocessError):
                raise PacketRejected("numerical_audit") from None
            if len(result.stdout) > MAX_BYTES or result.stderr:
                raise PacketRejected("numerical_audit")
            require_equal(read_json(result.stdout), audits[group])
    return {"schema_version": "tuc.supplied_model_candidate_offline_audit.v0", "status": "PASS",
            "scope": "fixed_candidate_record_consistency", "source_commit": SOURCE,
            "supplied_wheel_sha256": WHEEL, "procedure_sha256": PROCEDURE,
            "input_sha256": {name: sha256(value).hexdigest() for name, value in data.items()},
            "numerical_audits": audits, "lifecycle_claims_consistent": True,
            "tuc_imported": False, "native_execution_performed": False,
            "external_origin_verified": False, "independent_operator_acceptance": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory", type=Path, help="returned supplied-wheel observation directory",
    )
    args = parser.parse_args()
    try:
        report = audit(args.directory)
    except PacketRejected as error:
        sys.stdout.buffer.write(encoded({"status": "REJECTED", "reason": str(error)}))
        return 1
    sys.stdout.buffer.write(encoded(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
