"""Inert request/response boundary for the explicit bounded OCI source bridge.

Source is UTF-8 data here: this module neither parses its syntax nor launches a
worker. The response contract assumes the separately controlled, fixed worker;
its digests bind data and are not authentication or independent semantic proof.
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import NoReturn, cast

from tuc.compiler.bounded_cpu_json import _decode, source_intent_from_json
from tuc.frontend.source_intent import SourceIntentModule
from tuc.frontend.source_to_intent_research_kernel_ingress import (
    SourceToIntentResearchKernelIngressReport,
    source_to_intent_research_kernel_ingress_report_to_dict,
)

MAX_SOURCE_BYTES = 65536
MAX_SOURCE_LINES = 2048
MAX_SIGNATURE_BYTES = 16384
MAX_REQUEST_BYTES = 96 * 1024
MAX_RESPONSE_BYTES = 262144
SIGNATURE_SCHEMA_VERSION = "tuc.bounded_cpu_source.v0"
WORKER_PROTOCOL = "tuc.oci_source_ingestion_worker.v0"
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}\Z")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_SIGNATURE_KEYS = frozenset({"schema_version", "source_name", "kernel_name", "tensor_shapes"})
_PAYLOAD_KEYS = frozenset({"module_source", "source_name", "kernel_name", "tensor_shapes"})
_ACCEPTED_KEYS = frozenset({"protocol", "request_digest", "status", "security",
                            "ingress_report", "source_intent_payload"})
_SECURITY: dict[str, object] = {
    "address_space_bytes": 768 * 1024 * 1024,
    "capability_effective_hex": "0000000000000000",
    "core_dump_disabled": True,
    "cpu_period_micros": 100000,
    "cpu_quota_micros": 100000,
    "cpu_seconds": 4,
    "empty_working_directory": True,
    "file_size_bytes": 256 * 1024,
    "filesystem_namespace_isolation": True,
    "gid": 10001,
    "isolated_python_mode": True,
    "kernel_network_isolation": True,
    "memory_limit_bytes": 1024 * 1024 * 1024,
    "network_route_count": 0,
    "no_new_privileges": True,
    "open_files": 32,
    "pids_limit": 32,
    "repository_bind_mount": False,
    "root_filesystem_read_only": True,
    "seccomp_mode": 2,
    "shell": False,
    "tmpfs_nodev": True,
    "tmpfs_noexec": True,
    "tmpfs_nosuid": True,
    "uid": 10001,
}


class BoundedCPUSourceError(ValueError):
    """Closed, source-free diagnostic for the pure source protocol boundary."""

    def __init__(self, reason: str) -> None:
        if type(reason) is not str or reason not in (
                "signature_rejected", "source_rejected", "protocol_rejected", "graph_rejected"):
            raise ValueError("invalid bounded CPU source diagnostic")
        self._reason = reason
        super().__init__(reason)

    @property
    def reason(self) -> str:
        return self._reason


def _reject() -> NoReturn:
    raise ValueError("bounded CPU source rejected")


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _digest(value: bytes) -> str:
    return "sha256:" + sha256(value).hexdigest()


def _object(value: object, keys: frozenset[str]) -> dict[str, object]:
    if type(value) is not dict or frozenset(value) != keys:
        _reject()
    return cast(dict[str, object], value)


def _name(value: object) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        _reject()
    return value


def _signature(data: bytes) -> dict[str, object]:
    value = _decode(data, max_bytes=MAX_SIGNATURE_BYTES, max_depth=6,
                    max_tokens=2048, inputs=False)
    signature = _object(value, _SIGNATURE_KEYS)
    if signature["schema_version"] != SIGNATURE_SCHEMA_VERSION:
        _reject()
    _name(signature["source_name"])
    _name(signature["kernel_name"])
    shapes = signature["tensor_shapes"]
    if type(shapes) is not dict or not 1 <= len(shapes) <= 24:
        _reject()
    for name, shape in shapes.items():
        _name(name)
        if (type(shape) is not list or not 1 <= len(shape) <= 2 or
                any(type(d) is not int or not 1 <= d <= 64 for d in shape)):
            _reject()
    return signature


def _source(data: bytes) -> str:
    if (type(data) is not bytes or not 1 <= len(data) <= MAX_SOURCE_BYTES or
            data.startswith(b"\xef\xbb\xbf") or b"\x00" in data):
        _reject()
    source = data.decode("utf-8", errors="strict")
    if not 1 <= len(source.splitlines()) <= MAX_SOURCE_LINES:
        _reject()
    return source


def prepare_source_request(source: bytes, signature: bytes) -> bytes:
    """Validate bytes and a closed signature, without parsing source syntax.

    The returned compact JSON is the existing fixed OCI worker protocol. The
    worker's smaller request bound also applies after JSON escaping of source.
    """
    try:
        text = _source(source)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedCPUSourceError("source_rejected") from None
    try:
        declared = _signature(signature)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedCPUSourceError("signature_rejected") from None
    payload = {key: value for key, value in declared.items() if key != "schema_version"}
    payload["module_source"] = text
    request = _json({"protocol": WORKER_PROTOCOL, "payload": payload,
                     "request_digest": _digest(_json(payload))})
    if len(request) > MAX_REQUEST_BYTES:
        raise BoundedCPUSourceError("source_rejected")
    return request


def _request(data: bytes) -> dict[str, object]:
    value = _decode(data, max_bytes=MAX_REQUEST_BYTES, max_depth=7,
                    max_tokens=2048, inputs=False)
    request = _object(value, frozenset({"protocol", "request_digest", "payload"}))
    payload = _object(request["payload"], _PAYLOAD_KEYS)
    source = payload["module_source"]
    if type(source) is not str:
        _reject()
    signature = {key: item for key, item in payload.items() if key != "module_source"}
    signature["schema_version"] = SIGNATURE_SCHEMA_VERSION
    # Reconstruct through the public byte boundary, including the escape budget.
    if data != prepare_source_request(source.encode("utf-8"), _json(signature)):
        _reject()
    return request


def _exact(value: object, expected: object) -> None:
    """Compare already bounded plain JSON without bool/int equality aliases."""
    if type(value) is not type(expected):
        _reject()
    if type(expected) is dict:
        actual = cast(dict[str, object], value)
        template = cast(dict[str, object], expected)
        if actual.keys() != template.keys():
            _reject()
        for key, item in template.items():
            _exact(actual[key], item)
    elif type(expected) is list:
        actual_items = cast(list[object], value)
        template_items = cast(list[object], expected)
        if len(actual_items) != len(template_items):
            _reject()
        for actual_item, template_item in zip(actual_items, template_items, strict=True):
            _exact(actual_item, template_item)
    elif value != expected:
        _reject()


def _canonical_graph(module: SourceIntentModule) -> dict[str, object]:
    operations: list[dict[str, object]] = []
    for op in module.operations:
        if op.name != op.outputs[0] or op.hints:
            _reject()
        operation: dict[str, object] = {
            "name": op.name, "family": op.family, "inputs": list(op.inputs),
            "outputs": list(op.outputs), "hints": {},
        }
        if op.attributes:
            operation["attributes"] = dict(op.attributes)
        operations.append(operation)
    return {
        "schema_version": "source_intent.v0", "name": module.name,
        "tensors": [{"name": t.name, "shape": list(t.shape), "dtype": t.dtype}
                    for t in module.tensors],
        "operations": operations,
        "returns": [{"public_name": r.public_name, "tensor_name": r.tensor_name,
                     "required": True} for r in module.returns],
    }


def _bound_graph(value: object, payload: dict[str, object]) -> tuple[SourceIntentModule, bytes]:
    module = source_intent_from_json(_json(value))
    if module.name != payload["source_name"]:
        _reject()
    canonical = _canonical_graph(module)
    _exact(value, canonical)
    shapes = cast(dict[str, list[int]], payload["tensor_shapes"])
    tensors = {t.name: t for t in module.tensors}
    produced = {name for op in module.operations for name in op.outputs}
    external = set(tensors) - produced
    public = {returned.public_name for returned in module.returns}
    if external & public or produced & shapes.keys() or external | public != shapes.keys():
        _reject()
    for tensor in module.tensors:
        _name(tensor.name)
    for name in external:
        if list(tensors[name].shape) != shapes[name]:
            _reject()
    for returned in module.returns:
        _name(returned.public_name)
        if list(tensors[returned.tensor_name].shape) != shapes[returned.public_name]:
            _reject()
    return module, _json(canonical) + b"\n"


def _report(value: object, payload: dict[str, object], module: SourceIntentModule,
            graph: object) -> None:
    if type(value) is not dict:
        _reject()
    report = cast(dict[str, object], value)
    for key, limit in (("module_ast_node_count", 8192), ("module_ast_depth", 64)):
        count = report.get(key)
        if type(count) is not int or not 1 <= count <= limit:
            _reject()
    for key in ("extracted_kernel_digest", "parser_report_digest"):
        digest = report.get(key)
        if type(digest) is not str or _DIGEST.fullmatch(digest) is None:
            _reject()
    source = cast(str, payload["module_source"])
    # These two digests and AST measurements are worker observations, not facts
    # independently reproduced here: reproducing them would parse source on host.
    expected = SourceToIntentResearchKernelIngressReport(
        source_name=cast(str, payload["source_name"]),
        kernel_name=cast(str, payload["kernel_name"]),
        module_digest=_digest(source.encode("utf-8")),
        extracted_kernel_digest=cast(str, report["extracted_kernel_digest"]),
        parser_report_digest=cast(str, report["parser_report_digest"]),
        source_intent_digest=_digest(_json(graph)),
        module_bytes=len(source.encode("utf-8")), module_line_count=len(source.splitlines()),
        module_ast_node_count=cast(int, report["module_ast_node_count"]),
        module_ast_depth=cast(int, report["module_ast_depth"]),
        import_count=2, top_level_function_count=1,
        operation_families=tuple(sorted({op.family for op in module.operations})),
        tensor_count=len(module.tensors), operation_count=len(module.operations),
        return_count=len(module.returns),
    )
    _exact(report, source_to_intent_research_kernel_ingress_report_to_dict(expected))


def decode_source_response(request: bytes, response: bytes) -> bytes:
    """Return canonical bounded graph JSON only after exact request/worker checks.

    Only the separate runtime may launch the fixed OCI worker. This function
    treats both arguments as hostile bounded data and starts no AST parser.
    """
    try:
        declared = _request(request)
        decoded = _decode(response, max_bytes=MAX_RESPONSE_BYTES, max_depth=16,
                          max_tokens=16384, inputs=False)
        if type(decoded) is not dict:
            _reject()
        wire = cast(dict[str, object], decoded)
        if (wire.get("protocol") != WORKER_PROTOCOL or
                wire.get("request_digest") != declared["request_digest"]):
            _reject()
        if wire.get("status") == "rejected":
            _object(wire, frozenset({"protocol", "request_digest", "status", "reason_code"}))
            if wire["reason_code"] not in ("source_rejected", "protocol_rejected"):
                _reject()
        else:
            _object(wire, _ACCEPTED_KEYS)
            if wire["status"] != "accepted":
                _reject()
            _exact(wire["security"], _SECURITY)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedCPUSourceError("protocol_rejected") from None
    if wire["status"] == "rejected":
        raise BoundedCPUSourceError(cast(str, wire["reason_code"]))
    payload = cast(dict[str, object], declared["payload"])
    try:
        module, result = _bound_graph(wire["source_intent_payload"], payload)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedCPUSourceError("graph_rejected") from None
    try:
        _report(wire["ingress_report"], payload, module, wire["source_intent_payload"])
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedCPUSourceError("protocol_rejected") from None
    return result


__all__ = ["BoundedCPUSourceError", "MAX_SOURCE_BYTES", "MAX_SOURCE_LINES",
           "MAX_SIGNATURE_BYTES", "MAX_REQUEST_BYTES", "MAX_RESPONSE_BYTES",
           "SIGNATURE_SCHEMA_VERSION", "WORKER_PROTOCOL", "prepare_source_request",
           "decode_source_response"]
