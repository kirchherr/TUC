"""Private fixed-process entry point for isolated research source ingestion."""

from __future__ import annotations

import json
import resource
import sys
from hashlib import sha256
from pathlib import Path
from typing import cast

_PROTOCOL = "tuc.isolated_source_ingestion_worker.v0"
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

    _apply_limits()
    request_digest = "sha256:" + "0" * 64
    response: dict[str, object]
    try:
        request = _read_request()
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
            "protocol": _PROTOCOL,
            "request_digest": request_digest,
            "security": _security_facts(),
            "source_intent_payload": result.parser_result.source_intent_payload,
            "status": "accepted",
        }
    except (TypeError, ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        response = {
            "protocol": _PROTOCOL,
            "reason_code": "source_rejected",
            "request_digest": request_digest,
            "status": "rejected",
        }
    _write_response(response)
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


def _read_request() -> dict[str, object]:
    data = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
    if not data or len(data) > _MAX_REQUEST_BYTES:
        raise ValueError("request size rejected")
    request = json.loads(data.decode("utf-8", errors="strict"))
    if type(request) is not dict or frozenset(request) != _REQUEST_KEYS:
        raise ValueError("request shape rejected")
    typed = cast(dict[str, object], request)
    if typed.get("protocol") != _PROTOCOL:
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


def _security_facts() -> dict[str, object]:
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


def _write_response(response: dict[str, object]) -> None:
    data = _canonical_json(response).encode("utf-8")
    if len(data) > _MAX_RESPONSE_BYTES:
        data = _canonical_json(
            {
                "protocol": _PROTOCOL,
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
