"""Isolated, non-admitting research worker for bounded source ingestion.

The parent starts one fixed TUC worker in Python isolated mode, sends a bounded
JSON request over stdin, and independently validates the returned Source Intent
plain data. The worker is a research containment boundary, not a production
sandbox or a source-ingestion admission decision.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import cast

from tuc.frontend.source_intent import SourceIntentModule
from tuc.frontend.source_intent_intake import source_intent_from_mapping
from tuc.frontend.source_to_intent_research_kernel_ingress import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_ALLOWED_IMPORT_ALIASES,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REPORT_SCHEMA_VERSION,
)
from tuc.frontend.source_to_intent_research_parser import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
)
from tuc.frontend.triton_source import MAX_TRITON_SOURCE_BYTES

ISOLATED_SOURCE_INGESTION_CONTRACT = (
    "isolated_source_ingestion.research_non_admitting.v0"
)
ISOLATED_SOURCE_INGESTION_WORKER_PROTOCOL = (
    "tuc.isolated_source_ingestion_worker.v0"
)
ISOLATED_SOURCE_INGESTION_STATUS = "research_prototype_non_admitting"
ISOLATED_SOURCE_INGESTION_ADMISSION_EFFECT = (
    "does_not_admit_production_source_ingestion"
)
ISOLATED_SOURCE_INGESTION_OUTPUT_POLICY = (
    "validated_source_intent_internal_report_digest_only"
)
ISOLATED_SOURCE_INGESTION_RAW_SOURCE_POLICY = "omitted_from_public_evidence"
ISOLATED_SOURCE_INGESTION_ENFORCED_CONTROLS = (
    "address_space_limit",
    "core_dump_disabled",
    "cpu_time_limit",
    "empty_working_directory",
    "file_size_limit",
    "fixed_worker_path",
    "isolated_python_mode",
    "minimal_environment",
    "open_file_limit",
    "parent_wall_clock_timeout",
    "request_byte_limit",
    "response_byte_limit",
    "shell_disabled",
    "strict_response_revalidation",
)
ISOLATED_SOURCE_INGESTION_EXPLICIT_NON_CLAIMS = (
    "filesystem_namespace_isolation",
    "kernel_network_isolation",
    "native_code_sandbox",
    "production_source_ingestion",
    "production_source_sandbox",
)
ISOLATED_SOURCE_INGESTION_BLOCKED_EXECUTION_SURFACES = (
    "arbitrary_command_execution",
    "decorator_evaluation",
    "device_access",
    "dynamic_library_loading",
    "generated_artifact_execution",
    "jit_execution",
    "plugin_discovery",
    "source_module_import_execution",
    "source_text_execution",
    "user_selected_subprocess",
)

MAX_ISOLATED_SOURCE_INGESTION_REQUEST_BYTES = 96 * 1024
MAX_ISOLATED_SOURCE_INGESTION_RESPONSE_BYTES = 256 * 1024
ISOLATED_SOURCE_INGESTION_CPU_SECONDS = 4
ISOLATED_SOURCE_INGESTION_ADDRESS_SPACE_BYTES = 768 * 1024 * 1024
ISOLATED_SOURCE_INGESTION_OPEN_FILES = 32
ISOLATED_SOURCE_INGESTION_WALL_SECONDS = 8.0
ISOLATED_SOURCE_INGESTION_FILE_SIZE_BYTES = (
    MAX_ISOLATED_SOURCE_INGESTION_RESPONSE_BYTES
)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REQUEST_PAYLOAD_KEYS = frozenset(
    {"kernel_name", "module_source", "source_name", "tensor_shapes"}
)
_RESPONSE_KEYS = frozenset(
    {
        "ingress_report",
        "protocol",
        "request_digest",
        "security",
        "source_intent_payload",
        "status",
    }
)
_SECURITY_KEYS = frozenset(
    {
        "address_space_bytes",
        "core_dump_disabled",
        "cpu_seconds",
        "empty_working_directory",
        "file_size_bytes",
        "filesystem_namespace_isolation",
        "isolated_python_mode",
        "kernel_network_isolation",
        "open_files",
        "shell",
    }
)
_INGRESS_REPORT_KEYS = frozenset(
    {
        "allowed_import_aliases",
        "blocked_claims",
        "blocked_compiler_outputs",
        "blocked_execution_surfaces",
        "default_parser_status",
        "extracted_kernel_digest",
        "import_count",
        "ingress_contract",
        "input_policy",
        "kernel_name",
        "module_ast_depth",
        "module_ast_node_count",
        "module_bytes",
        "module_digest",
        "module_line_count",
        "operation_count",
        "operation_families",
        "output_policy",
        "parser_output_policy",
        "parser_report_digest",
        "parser_status",
        "raw_source_policy",
        "raw_value_policy",
        "return_count",
        "schema_version",
        "source_intent_digest",
        "source_name",
        "tensor_count",
        "top_level_function_count",
    }
)


class IsolatedSourceIngestionError(ValueError):
    """Raised when the worker or its fail-closed protocol is rejected."""


@dataclass(frozen=True)
class IsolatedSourceIngestionReport:
    """Source-free metadata for one accepted isolated research parse."""

    source_name: str
    kernel_name: str
    request_digest: str
    module_digest: str
    source_intent_digest: str
    ingress_report_digest: str
    operation_families: tuple[str, ...]
    tensor_count: int
    operation_count: int
    return_count: int
    contract: str = ISOLATED_SOURCE_INGESTION_CONTRACT
    worker_protocol: str = ISOLATED_SOURCE_INGESTION_WORKER_PROTOCOL
    status: str = ISOLATED_SOURCE_INGESTION_STATUS
    admission_effect: str = ISOLATED_SOURCE_INGESTION_ADMISSION_EFFECT
    output_policy: str = ISOLATED_SOURCE_INGESTION_OUTPUT_POLICY
    raw_source_policy: str = ISOLATED_SOURCE_INGESTION_RAW_SOURCE_POLICY
    enforced_controls: tuple[str, ...] = ISOLATED_SOURCE_INGESTION_ENFORCED_CONTROLS
    explicit_non_claims: tuple[str, ...] = (
        ISOLATED_SOURCE_INGESTION_EXPLICIT_NON_CLAIMS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        ISOLATED_SOURCE_INGESTION_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_identifier(self.source_name, "source_name")
        _validate_identifier(self.kernel_name, "kernel_name")
        for value, label in (
            (self.request_digest, "request_digest"),
            (self.module_digest, "module_digest"),
            (self.source_intent_digest, "source_intent_digest"),
            (self.ingress_report_digest, "ingress_report_digest"),
        ):
            _validate_digest(value, label)
        if self.contract != ISOLATED_SOURCE_INGESTION_CONTRACT:
            raise IsolatedSourceIngestionError("isolated ingestion contract drift")
        if self.worker_protocol != ISOLATED_SOURCE_INGESTION_WORKER_PROTOCOL:
            raise IsolatedSourceIngestionError("isolated ingestion protocol drift")
        if self.status != ISOLATED_SOURCE_INGESTION_STATUS:
            raise IsolatedSourceIngestionError("isolated ingestion status drift")
        if self.admission_effect != ISOLATED_SOURCE_INGESTION_ADMISSION_EFFECT:
            raise IsolatedSourceIngestionError("isolated ingestion admission drift")
        if self.output_policy != ISOLATED_SOURCE_INGESTION_OUTPUT_POLICY:
            raise IsolatedSourceIngestionError("isolated ingestion output drift")
        if self.raw_source_policy != ISOLATED_SOURCE_INGESTION_RAW_SOURCE_POLICY:
            raise IsolatedSourceIngestionError("isolated ingestion source policy drift")
        if self.enforced_controls != ISOLATED_SOURCE_INGESTION_ENFORCED_CONTROLS:
            raise IsolatedSourceIngestionError("isolated ingestion controls drift")
        if self.explicit_non_claims != ISOLATED_SOURCE_INGESTION_EXPLICIT_NON_CLAIMS:
            raise IsolatedSourceIngestionError("isolated ingestion non-claims drift")
        if self.blocked_execution_surfaces != (
            ISOLATED_SOURCE_INGESTION_BLOCKED_EXECUTION_SURFACES
        ):
            raise IsolatedSourceIngestionError("isolated ingestion surfaces drift")
        _validate_count(self.tensor_count, "tensor_count")
        _validate_count(self.operation_count, "operation_count")
        _validate_count(self.return_count, "return_count")
        _validate_operation_families(self.operation_families)


@dataclass(frozen=True)
class IsolatedSourceIngestionResult:
    """Validated internal Source Intent plus source-free worker evidence."""

    module: SourceIntentModule
    report: IsolatedSourceIngestionReport


def ingest_isolated_triton_module_source(
    module_source: str,
    *,
    source_name: str,
    kernel_name: str,
    tensor_shapes: Mapping[str, Sequence[int]],
) -> IsolatedSourceIngestionResult:
    """Parse one bounded module in the fixed non-admitting research worker."""

    if not sys.platform.startswith("linux"):
        raise IsolatedSourceIngestionError(
            "isolated source ingestion worker requires Linux resource controls"
        )
    payload = _build_request_payload(
        module_source,
        source_name=source_name,
        kernel_name=kernel_name,
        tensor_shapes=tensor_shapes,
    )
    request_digest = _digest_payload(payload)
    request = {
        "payload": payload,
        "protocol": ISOLATED_SOURCE_INGESTION_WORKER_PROTOCOL,
        "request_digest": request_digest,
    }
    request_bytes = _canonical_json(request).encode("utf-8")
    if len(request_bytes) > MAX_ISOLATED_SOURCE_INGESTION_REQUEST_BYTES:
        raise IsolatedSourceIngestionError("isolated ingestion request exceeds limit")

    response = _run_fixed_worker(request_bytes)
    return _result_from_worker_response(
        response,
        expected_request_digest=request_digest,
        expected_source_name=source_name,
        expected_kernel_name=kernel_name,
        expected_module_source=module_source,
    )


def isolated_source_ingestion_report_to_dict(
    report: IsolatedSourceIngestionReport,
) -> dict[str, object]:
    """Return stable metadata-only evidence without source or Source Intent data."""

    if not isinstance(report, IsolatedSourceIngestionReport):
        raise TypeError("isolated source ingestion report must be report object")
    return {
        "admission_effect": report.admission_effect,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "contract": report.contract,
        "direct_source_ingestion": False,
        "enforced_controls": list(report.enforced_controls),
        "explicit_non_claims": list(report.explicit_non_claims),
        "filesystem_namespace_isolation": False,
        "ingress_report_digest": report.ingress_report_digest,
        "kernel_name": report.kernel_name,
        "kernel_network_isolation": False,
        "module_digest": report.module_digest,
        "operation_count": report.operation_count,
        "operation_families": list(report.operation_families),
        "output_policy": report.output_policy,
        "production_source_ingestion": False,
        "raw_source_policy": report.raw_source_policy,
        "raw_source_serialized": False,
        "request_digest": report.request_digest,
        "research_source_to_intent_plain_data": True,
        "return_count": report.return_count,
        "source_intent_digest": report.source_intent_digest,
        "source_intent_payload_serialized": False,
        "source_name": report.source_name,
        "source_text_executed": False,
        "status": report.status,
        "tensor_count": report.tensor_count,
        "worker_protocol": report.worker_protocol,
    }


def _build_request_payload(
    module_source: object,
    *,
    source_name: object,
    kernel_name: object,
    tensor_shapes: object,
) -> dict[str, object]:
    if not isinstance(module_source, str):
        raise TypeError("isolated ingestion module source must be text")
    try:
        source_bytes = len(module_source.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise IsolatedSourceIngestionError(
            "isolated ingestion source must be valid UTF-8"
        ) from exc
    if source_bytes == 0:
        raise IsolatedSourceIngestionError("isolated ingestion source must not be empty")
    if source_bytes > MAX_TRITON_SOURCE_BYTES:
        raise IsolatedSourceIngestionError("isolated ingestion source exceeds limit")
    _validate_identifier(source_name, "source_name")
    _validate_identifier(kernel_name, "kernel_name")
    shapes = _plain_shape_manifest(tensor_shapes)
    return {
        "kernel_name": kernel_name,
        "module_source": module_source,
        "source_name": source_name,
        "tensor_shapes": shapes,
    }


def _plain_shape_manifest(value: object) -> dict[str, list[int]]:
    if type(value) is not dict:
        raise TypeError("isolated ingestion tensor_shapes must be a plain mapping")
    mapping = cast(dict[object, object], value)
    if not mapping or len(mapping) > 64:
        raise IsolatedSourceIngestionError("isolated ingestion shape count invalid")
    result: dict[str, list[int]] = {}
    for key in mapping:
        _validate_identifier(key, "tensor shape name")
    for key in sorted(cast(dict[str, object], mapping)):
        raw_shape = mapping[key]
        if type(raw_shape) not in {list, tuple}:
            raise TypeError("isolated ingestion tensor shape must be plain sequence")
        shape = cast(Sequence[object], raw_shape)
        if not shape or len(shape) > 8:
            raise IsolatedSourceIngestionError("isolated ingestion tensor rank invalid")
        dimensions: list[int] = []
        for dimension in shape:
            if (
                not isinstance(dimension, int)
                or isinstance(dimension, bool)
                or dimension <= 0
                or dimension > 2**31 - 1
            ):
                raise IsolatedSourceIngestionError(
                    "isolated ingestion tensor dimension invalid"
                )
            dimensions.append(dimension)
        result[key] = dimensions
    return result


def _run_fixed_worker(request_bytes: bytes) -> object:
    command = _fixed_worker_command()
    environment = {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUTF8": "1",
    }
    with (
        tempfile.TemporaryDirectory(prefix="tuc-source-worker-") as workdir,
        tempfile.TemporaryFile() as stdout_file,
        tempfile.TemporaryFile() as stderr_file,
    ):
        process = subprocess.Popen(  # noqa: S603 - fixed trusted worker only
            command,
            stdin=subprocess.PIPE,
            stdout=stdout_file,
            stderr=stderr_file,
            cwd=workdir,
            env=environment,
            shell=False,
            close_fds=True,
            start_new_session=True,
        )
        try:
            process.communicate(
                input=request_bytes,
                timeout=ISOLATED_SOURCE_INGESTION_WALL_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            _terminate_worker(process)
            raise IsolatedSourceIngestionError(
                "isolated ingestion worker exceeded wall-clock limit"
            ) from exc
        if process.returncode != 0:
            raise IsolatedSourceIngestionError("isolated ingestion worker failed closed")
        stderr_bytes = _read_bounded_file(
            stderr_file,
            MAX_ISOLATED_SOURCE_INGESTION_RESPONSE_BYTES,
            "stderr",
        )
        if stderr_bytes:
            raise IsolatedSourceIngestionError(
                "isolated ingestion worker emitted diagnostics outside protocol"
            )
        response_bytes = _read_bounded_file(
            stdout_file,
            MAX_ISOLATED_SOURCE_INGESTION_RESPONSE_BYTES,
            "response",
        )
    try:
        response_text = response_bytes.decode("utf-8", errors="strict")
        return json.loads(response_text)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise IsolatedSourceIngestionError(
            "isolated ingestion worker returned invalid JSON"
        ) from exc


def _fixed_worker_command() -> tuple[str, ...]:
    worker_path = Path(__file__).with_name("_isolated_source_ingestion_worker.py")
    resolved = worker_path.resolve(strict=True)
    return (sys.executable, "-I", str(resolved))


def _terminate_worker(process: subprocess.Popen[bytes]) -> None:
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def _read_bounded_file(file: object, limit: int, label: str) -> bytes:
    file.seek(0, os.SEEK_END)  # type: ignore[attr-defined]
    size = file.tell()  # type: ignore[attr-defined]
    if not isinstance(size, int) or size < 0 or size > limit:
        raise IsolatedSourceIngestionError(
            f"isolated ingestion worker {label} exceeds limit"
        )
    file.seek(0)  # type: ignore[attr-defined]
    data = file.read(limit + 1)  # type: ignore[attr-defined]
    if not isinstance(data, bytes) or len(data) > limit:
        raise IsolatedSourceIngestionError(
            f"isolated ingestion worker {label} exceeds limit"
        )
    return data


def _result_from_worker_response(
    response: object,
    *,
    expected_request_digest: str,
    expected_source_name: str,
    expected_kernel_name: str,
    expected_module_source: str,
) -> IsolatedSourceIngestionResult:
    if type(response) is not dict:
        raise IsolatedSourceIngestionError("isolated ingestion response must be object")
    payload = cast(dict[str, object], response)
    if payload.get("protocol") != ISOLATED_SOURCE_INGESTION_WORKER_PROTOCOL:
        raise IsolatedSourceIngestionError("isolated ingestion response protocol drift")
    if payload.get("request_digest") != expected_request_digest:
        raise IsolatedSourceIngestionError("isolated ingestion request binding drift")
    status = payload.get("status")
    if status == "rejected":
        if set(payload) != {"protocol", "reason_code", "request_digest", "status"}:
            raise IsolatedSourceIngestionError("isolated ingestion rejection key drift")
        if payload.get("reason_code") not in {"protocol_rejected", "source_rejected"}:
            raise IsolatedSourceIngestionError("isolated ingestion rejection reason drift")
        raise IsolatedSourceIngestionError(
            f"isolated ingestion worker rejected request: {payload['reason_code']}"
        )
    if status != "accepted" or frozenset(payload) != _RESPONSE_KEYS:
        raise IsolatedSourceIngestionError("isolated ingestion response key drift")
    _validate_worker_security(payload["security"])
    source_intent_payload = payload["source_intent_payload"]
    if type(source_intent_payload) is not dict:
        raise IsolatedSourceIngestionError(
            "isolated ingestion Source Intent must be plain object"
        )
    try:
        module = source_intent_from_mapping(source_intent_payload)
    except (TypeError, ValueError) as exc:
        raise IsolatedSourceIngestionError(
            "isolated ingestion Source Intent failed parent validation"
        ) from exc
    ingress = _validate_ingress_report(
        payload["ingress_report"],
        expected_source_name=expected_source_name,
        expected_kernel_name=expected_kernel_name,
        expected_module_source=expected_module_source,
        source_intent_payload=cast(dict[str, object], source_intent_payload),
    )
    return IsolatedSourceIngestionResult(
        module=module,
        report=IsolatedSourceIngestionReport(
            source_name=expected_source_name,
            kernel_name=expected_kernel_name,
            request_digest=expected_request_digest,
            module_digest=cast(str, ingress["module_digest"]),
            source_intent_digest=cast(str, ingress["source_intent_digest"]),
            ingress_report_digest=_digest_payload(ingress),
            operation_families=tuple(cast(list[str], ingress["operation_families"])),
            tensor_count=cast(int, ingress["tensor_count"]),
            operation_count=cast(int, ingress["operation_count"]),
            return_count=cast(int, ingress["return_count"]),
        ),
    )


def _validate_worker_security(value: object) -> None:
    if type(value) is not dict:
        raise IsolatedSourceIngestionError("isolated ingestion security must be object")
    security = cast(dict[str, object], value)
    if frozenset(security) != _SECURITY_KEYS:
        raise IsolatedSourceIngestionError("isolated ingestion security key drift")
    expected: dict[str, object] = {
        "address_space_bytes": ISOLATED_SOURCE_INGESTION_ADDRESS_SPACE_BYTES,
        "core_dump_disabled": True,
        "cpu_seconds": ISOLATED_SOURCE_INGESTION_CPU_SECONDS,
        "empty_working_directory": True,
        "file_size_bytes": ISOLATED_SOURCE_INGESTION_FILE_SIZE_BYTES,
        "filesystem_namespace_isolation": False,
        "isolated_python_mode": True,
        "kernel_network_isolation": False,
        "open_files": ISOLATED_SOURCE_INGESTION_OPEN_FILES,
        "shell": False,
    }
    if security != expected:
        raise IsolatedSourceIngestionError("isolated ingestion security drift")


def _validate_ingress_report(
    value: object,
    *,
    expected_source_name: str,
    expected_kernel_name: str,
    expected_module_source: str,
    source_intent_payload: dict[str, object],
) -> dict[str, object]:
    if type(value) is not dict:
        raise IsolatedSourceIngestionError("isolated ingestion report must be object")
    report = cast(dict[str, object], value)
    if frozenset(report) != _INGRESS_REPORT_KEYS:
        raise IsolatedSourceIngestionError("isolated ingestion ingress key drift")
    expected_values: dict[str, object] = {
        "allowed_import_aliases": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_ALLOWED_IMPORT_ALIASES
        ),
        "blocked_claims": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS
        ),
        "blocked_compiler_outputs": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS
        ),
        "blocked_execution_surfaces": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES
        ),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "input_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY,
        "kernel_name": expected_kernel_name,
        "module_bytes": len(expected_module_source.encode("utf-8")),
        "module_digest": _digest_text(expected_module_source),
        "module_line_count": len(expected_module_source.splitlines()),
        "output_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY,
        "parser_output_policy": SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "schema_version": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REPORT_SCHEMA_VERSION,
        "source_intent_digest": _digest_payload(source_intent_payload),
        "source_name": expected_source_name,
        "import_count": 2,
        "top_level_function_count": 1,
    }
    for key, expected in expected_values.items():
        if report.get(key) != expected:
            raise IsolatedSourceIngestionError(
                f"isolated ingestion ingress {key} drift"
            )
    for key in (
        "module_ast_depth",
        "module_ast_node_count",
        "tensor_count",
        "operation_count",
        "return_count",
    ):
        _validate_count(report.get(key), key)
    for key in ("extracted_kernel_digest", "parser_report_digest"):
        _validate_digest(report.get(key), key)
    families = report.get("operation_families")
    if type(families) is not list or any(not isinstance(item, str) for item in families):
        raise IsolatedSourceIngestionError(
            "isolated ingestion operation families invalid"
        )
    _validate_operation_families(tuple(cast(list[str], families)))
    _validate_json_tree(report, depth=0)
    return report


def _validate_json_tree(value: object, *, depth: int) -> None:
    if depth > 32:
        raise IsolatedSourceIngestionError("isolated ingestion response depth exceeded")
    if value is None or type(value) in {bool, int, float, str}:
        return
    if type(value) is list:
        if len(cast(list[object], value)) > 4096:
            raise IsolatedSourceIngestionError("isolated ingestion response list too large")
        for item in cast(list[object], value):
            _validate_json_tree(item, depth=depth + 1)
        return
    if type(value) is dict:
        if len(cast(dict[object, object], value)) > 4096:
            raise IsolatedSourceIngestionError("isolated ingestion response object too large")
        for key, item in cast(dict[object, object], value).items():
            if not isinstance(key, str):
                raise IsolatedSourceIngestionError(
                    "isolated ingestion response keys must be strings"
                )
            _validate_json_tree(item, depth=depth + 1)
        return
    raise IsolatedSourceIngestionError("isolated ingestion response is not plain JSON")


def _validate_identifier(value: object, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise IsolatedSourceIngestionError(
            f"isolated ingestion {label} must be simple identifier"
        )


def _validate_digest(value: object, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise IsolatedSourceIngestionError(
            f"isolated ingestion {label} must be sha256"
        )


def _validate_count(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 4096:
        raise IsolatedSourceIngestionError(f"isolated ingestion {label} invalid")


def _validate_operation_families(values: tuple[str, ...]) -> None:
    if type(values) is not tuple or tuple(sorted(set(values))) != values:
        raise IsolatedSourceIngestionError(
            "isolated ingestion operation families invalid"
        )
    if any(value not in {"elementwise", "matmul", "reduction", "softmax"} for value in values):
        raise IsolatedSourceIngestionError(
            "isolated ingestion operation family unsupported"
        )


def _digest_payload(payload: object) -> str:
    return _digest_text(_canonical_json(payload))


def _digest_text(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


__all__ = [
    "ISOLATED_SOURCE_INGESTION_ADMISSION_EFFECT",
    "ISOLATED_SOURCE_INGESTION_BLOCKED_EXECUTION_SURFACES",
    "ISOLATED_SOURCE_INGESTION_CONTRACT",
    "ISOLATED_SOURCE_INGESTION_ENFORCED_CONTROLS",
    "ISOLATED_SOURCE_INGESTION_EXPLICIT_NON_CLAIMS",
    "ISOLATED_SOURCE_INGESTION_OUTPUT_POLICY",
    "ISOLATED_SOURCE_INGESTION_RAW_SOURCE_POLICY",
    "ISOLATED_SOURCE_INGESTION_STATUS",
    "ISOLATED_SOURCE_INGESTION_WORKER_PROTOCOL",
    "IsolatedSourceIngestionError",
    "IsolatedSourceIngestionReport",
    "IsolatedSourceIngestionResult",
    "ingest_isolated_triton_module_source",
    "isolated_source_ingestion_report_to_dict",
]
