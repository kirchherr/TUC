"""Private fixed-process entry point for isolated research source ingestion."""

from __future__ import annotations

import json
import os
import resource
import sys
from hashlib import sha256
from pathlib import Path
from typing import cast

_PROTOCOL = "tuc.isolated_source_ingestion_worker.v0"
_OCI_PROTOCOL = "tuc.oci_source_ingestion_worker.v0"
_MAX_REQUEST_BYTES = 96 * 1024
_MAX_RESPONSE_BYTES = 256 * 1024
_CPU_SECONDS = 4
_ADDRESS_SPACE_BYTES = 768 * 1024 * 1024
_OPEN_FILES = 32
_FILE_SIZE_BYTES = _MAX_RESPONSE_BYTES
_REQUEST_KEYS = frozenset({"payload", "protocol", "request_digest"})
_PAYLOAD_KEYS = frozenset(
    {"kernel_name", "module_source", "source_name", "tensor_shapes"}
)


def main() -> int:
    """Apply limits before loading TUC and process exactly one request."""

    oci_mode = _oci_mode()
    protocol = _OCI_PROTOCOL if oci_mode else _PROTOCOL
    _apply_limits()
    request_digest = "sha256:" + "0" * 64
    response: dict[str, object]
    try:
        security = _security_facts(oci_mode=oci_mode)
        request = _read_request(protocol)
        request_digest = cast(str, request["request_digest"])
        payload = cast(dict[str, object], request["payload"])
        _add_trusted_source_root()
        from tuc.frontend.source_to_intent_research_kernel_ingress import (
            ingest_triton_module_source_to_source_intent,
            source_to_intent_research_kernel_ingress_report_to_dict,
        )

        result = ingest_triton_module_source_to_source_intent(
            cast(str, payload["module_source"]),
            source_name=cast(str, payload["source_name"]),
            kernel_name=cast(str, payload["kernel_name"]),
            tensor_shapes=cast(dict[str, list[int]], payload["tensor_shapes"]),
        )
        response = {
            "ingress_report": source_to_intent_research_kernel_ingress_report_to_dict(
                result.report
            ),
            "protocol": protocol,
            "request_digest": request_digest,
            "security": security,
            "source_intent_payload": result.parser_result.source_intent_payload,
            "status": "accepted",
        }
    except (TypeError, ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        response = {
            "protocol": protocol,
            "reason_code": "source_rejected",
            "request_digest": request_digest,
            "status": "rejected",
        }
    _write_response(response, protocol=protocol)
    return 0


def _apply_limits() -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (_CPU_SECONDS, _CPU_SECONDS))
    resource.setrlimit(
        resource.RLIMIT_AS,
        (_ADDRESS_SPACE_BYTES, _ADDRESS_SPACE_BYTES),
    )
    resource.setrlimit(
        resource.RLIMIT_FSIZE,
        (_FILE_SIZE_BYTES, _FILE_SIZE_BYTES),
    )
    resource.setrlimit(resource.RLIMIT_NOFILE, (_OPEN_FILES, _OPEN_FILES))


def _read_request(protocol: str) -> dict[str, object]:
    data = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
    if not data or len(data) > _MAX_REQUEST_BYTES:
        raise ValueError("request size rejected")
    request = json.loads(data.decode("utf-8", errors="strict"))
    if type(request) is not dict or frozenset(request) != _REQUEST_KEYS:
        raise ValueError("request shape rejected")
    typed = cast(dict[str, object], request)
    if typed.get("protocol") != protocol:
        raise ValueError("request protocol rejected")
    payload = typed.get("payload")
    if type(payload) is not dict or frozenset(payload) != _PAYLOAD_KEYS:
        raise ValueError("request payload rejected")
    digest = typed.get("request_digest")
    if not isinstance(digest, str) or digest != _digest_payload(payload):
        raise ValueError("request digest rejected")
    if not isinstance(cast(dict[str, object], payload).get("module_source"), str):
        raise TypeError("module source rejected")
    return typed


def _add_trusted_source_root() -> None:
    source_root = Path(__file__).resolve(strict=True).parents[2]
    sys.path.insert(0, str(source_root))


def _security_facts(*, oci_mode: bool) -> dict[str, object]:
    if oci_mode:
        return _oci_security_facts()
    return {
        "address_space_bytes": _ADDRESS_SPACE_BYTES,
        "core_dump_disabled": True,
        "cpu_seconds": _CPU_SECONDS,
        "empty_working_directory": not any(Path.cwd().iterdir()),
        "file_size_bytes": _FILE_SIZE_BYTES,
        "filesystem_namespace_isolation": False,
        "isolated_python_mode": bool(sys.flags.isolated),
        "kernel_network_isolation": False,
        "open_files": _OPEN_FILES,
        "shell": False,
    }


def _oci_security_facts() -> dict[str, object]:
    status = _proc_status()
    root_options = _required_mount_options("/")
    tmp_options = _required_mount_options("/tmp")
    network_route_count = _network_route_count()
    repository_bind_mount = _mount_options("/workspace") is not None
    facts: dict[str, object] = {
        "address_space_bytes": _ADDRESS_SPACE_BYTES,
        "capability_effective_hex": status.get("CapEff", ""),
        "core_dump_disabled": True,
        "cpu_period_micros": _cgroup_cpu_limit()[1],
        "cpu_quota_micros": _cgroup_cpu_limit()[0],
        "cpu_seconds": _CPU_SECONDS,
        "empty_working_directory": not any(Path.cwd().iterdir()),
        "file_size_bytes": _FILE_SIZE_BYTES,
        "filesystem_namespace_isolation": (
            "ro" in root_options and not repository_bind_mount
        ),
        "gid": os.getgid(),
        "isolated_python_mode": bool(sys.flags.isolated),
        "kernel_network_isolation": network_route_count == 0,
        "memory_limit_bytes": _cgroup_int("memory.max"),
        "network_route_count": network_route_count,
        "no_new_privileges": status.get("NoNewPrivs") == "1",
        "open_files": _OPEN_FILES,
        "pids_limit": _cgroup_int("pids.max"),
        "repository_bind_mount": repository_bind_mount,
        "root_filesystem_read_only": "ro" in root_options,
        "seccomp_mode": int(status.get("Seccomp", "-1")),
        "shell": False,
        "tmpfs_nodev": "nodev" in tmp_options,
        "tmpfs_noexec": "noexec" in tmp_options,
        "tmpfs_nosuid": "nosuid" in tmp_options,
        "uid": os.getuid(),
    }
    _assert_oci_security_facts(facts)
    return facts


def _assert_oci_security_facts(facts: dict[str, object]) -> None:
    expected = {
        "capability_effective_hex": "0000000000000000",
        "cpu_period_micros": 100000,
        "cpu_quota_micros": 100000,
        "filesystem_namespace_isolation": True,
        "gid": 10001,
        "kernel_network_isolation": True,
        "memory_limit_bytes": 1024 * 1024 * 1024,
        "network_route_count": 0,
        "no_new_privileges": True,
        "pids_limit": 32,
        "repository_bind_mount": False,
        "root_filesystem_read_only": True,
        "seccomp_mode": 2,
        "tmpfs_nodev": True,
        "tmpfs_noexec": True,
        "tmpfs_nosuid": True,
        "uid": 10001,
    }
    for key, value in expected.items():
        if facts.get(key) != value:
            raise ValueError("OCI sandbox invariant rejected")


def _proc_status() -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key] = value.strip()
    return fields


def _required_mount_options(mount_point: str) -> frozenset[str]:
    options = _mount_options(mount_point)
    if options is None:
        raise ValueError("OCI sandbox mount invariant missing")
    return options


def _mount_options(mount_point: str) -> frozenset[str] | None:
    for line in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 6 and fields[4] == mount_point:
            return frozenset(fields[5].split(","))
    return None


def _network_route_count() -> int:
    lines = Path("/proc/net/route").read_text(encoding="utf-8").splitlines()
    return max(0, len(lines) - 1)


def _cgroup_int(name: str) -> int:
    value = Path("/sys/fs/cgroup", name).read_text(encoding="utf-8").strip()
    if not value.isdigit():
        raise ValueError("OCI sandbox cgroup invariant rejected")
    return int(value)


def _cgroup_cpu_limit() -> tuple[int, int]:
    values = Path("/sys/fs/cgroup/cpu.max").read_text(encoding="utf-8").split()
    if len(values) != 2 or any(not value.isdigit() for value in values):
        raise ValueError("OCI sandbox CPU invariant rejected")
    return int(values[0]), int(values[1])


def _oci_mode() -> bool:
    if len(sys.argv) == 1:
        return False
    if sys.argv[1:] == ["--oci"]:
        return True
    raise ValueError("worker invocation rejected")


def _write_response(response: dict[str, object], *, protocol: str) -> None:
    data = _canonical_json(response).encode("utf-8")
    if len(data) > _MAX_RESPONSE_BYTES:
        data = _canonical_json(
            {
                "protocol": protocol,
                "reason_code": "protocol_rejected",
                "request_digest": response.get(
                    "request_digest", "sha256:" + "0" * 64
                ),
                "status": "rejected",
            }
        ).encode("utf-8")
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def _digest_payload(payload: object) -> str:
    return f"sha256:{sha256(_canonical_json(payload).encode('utf-8')).hexdigest()}"


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


if __name__ == "__main__":
    raise SystemExit(main())
