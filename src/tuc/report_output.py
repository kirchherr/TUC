"""Fail-closed stdout boundary for public JSON evidence reports."""

from __future__ import annotations

import json
import math
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any

MAX_PUBLIC_REPORT_BYTES = 1_048_576
MAX_PUBLIC_REPORT_DEPTH = 32
MAX_PUBLIC_REPORT_ITEMS = 50_000
MAX_PUBLIC_REPORT_LINES = 10_000
MAX_PUBLIC_REPORT_LINE_LENGTH = 16_384
MAX_PUBLIC_REPORT_STRING_LENGTH = 65_536

_SECRET_FIELD_NAMES = frozenset(
    {
        "access_token",
        "api_key",
        "auth_token",
        "authorization",
        "client_secret",
        "cookie",
        "credential",
        "credentials",
        "password",
        "passwd",
        "private_key",
        "secret",
        "session_id",
    }
)
_CONDITIONAL_RAW_FIELD_NAMES = frozenset(
    {
        "artifact_bytes",
        "attestation_bundle",
        "command_line",
        "device_id",
        "device_identifier",
        "environment_variables",
        "host_path",
        "host_paths",
        "raw_source",
        "raw_tensor_values",
        "raw_values",
        "runtime_handle",
        "runtime_handles",
        "source_code",
        "source_text",
        "tensor_values",
    }
)
_SAFE_OMISSION_VALUES = frozenset(
    {
        "absent",
        "blocked",
        "not_present",
        "not_serialized",
        "omitted",
        "omitted_by_policy",
    }
)
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_SECRET_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)
_TEXT_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_TEXT_SECRET_ASSIGNMENT = re.compile(
    r"(?im)\b(?:access_token|api_key|auth_token|authorization|client_secret|"
    r"cookie|credential|credentials|password|passwd|private_key|secret|session_id)"
    r"\b\s*[:=]"
)
_TEXT_RAW_ASSIGNMENT = re.compile(
    r"(?im)\b(?:artifact_bytes|attestation_bundle|command_line|device_id|"
    r"device_identifier|environment_variables|host_path|host_paths|raw_source|"
    r"raw_tensor_values|raw_values|runtime_handle|runtime_handles|source_code|"
    r"source_text|tensor_values)\b\s*[:=]"
)
_TEXT_ABSOLUTE_PATH_ASSIGNMENT = re.compile(
    r"(?im)=\s*[\"']?(?:[A-Za-z]:[\\/]|/(?!/)|\\\\)"
)


class PublicReportOutputError(ValueError):
    """Raised when a report is unsafe to emit through the public boundary."""


def emit_public_json_report(report_text: str) -> None:
    """Validate and emit one bounded public JSON report exactly as supplied."""

    if not isinstance(report_text, str):
        raise TypeError("public report text must be a string")
    encoded = report_text.encode("utf-8")
    if not encoded:
        raise PublicReportOutputError("public report must not be empty")
    if len(encoded) > MAX_PUBLIC_REPORT_BYTES:
        raise PublicReportOutputError("public report exceeds byte limit")
    if not report_text.endswith("\n"):
        raise PublicReportOutputError("public report must end with one newline")

    try:
        payload = json.loads(
            report_text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_finite_constant,
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PublicReportOutputError("public report must be valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise PublicReportOutputError("public report root must be an object")

    item_count = [0]
    _validate_public_value(payload, path="$", depth=0, item_count=item_count)

    _emit_validated_report(encoded)


def emit_public_text_report(report_text: str) -> None:
    """Validate and emit one bounded public plain-text evidence report."""

    if not isinstance(report_text, str):
        raise TypeError("public report text must be a string")
    encoded = report_text.encode("utf-8")
    if not encoded:
        raise PublicReportOutputError("public report must not be empty")
    if len(encoded) > MAX_PUBLIC_REPORT_BYTES:
        raise PublicReportOutputError("public report exceeds byte limit")
    if not report_text.endswith("\n") or "\r" in report_text:
        raise PublicReportOutputError("public report must use LF and end with a newline")

    lines = report_text.splitlines()
    if len(lines) > MAX_PUBLIC_REPORT_LINES:
        raise PublicReportOutputError("public report exceeds line limit")
    if any(len(line) > MAX_PUBLIC_REPORT_LINE_LENGTH for line in lines):
        raise PublicReportOutputError("public report exceeds line-length limit")
    if _TEXT_CONTROL_CHARACTERS.search(report_text):
        raise PublicReportOutputError("public report contains control characters")
    if _TEXT_SECRET_ASSIGNMENT.search(report_text):
        raise PublicReportOutputError("public report contains sensitive assignment")
    if _TEXT_RAW_ASSIGNMENT.search(report_text):
        raise PublicReportOutputError("public report contains raw-data assignment")
    if _TEXT_ABSOLUTE_PATH_ASSIGNMENT.search(report_text):
        raise PublicReportOutputError("public report contains absolute path assignment")
    if any(pattern.search(report_text) for pattern in _SECRET_VALUE_PATTERNS):
        raise PublicReportOutputError("public report contains secret material")

    _emit_validated_report(encoded)


def _emit_validated_report(encoded: bytes) -> None:
    # Every caller size-bounds and validates the payload before this sole process-output
    # sink. Public reports exclude secrets, raw values, runtime handles, and host paths.
    # lgtm[py/clear-text-logging-sensitive-data]
    sys.stdout.buffer.write(encoded)


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PublicReportOutputError("public report contains duplicate keys")
        result[key] = value
    return result


def _reject_non_finite_constant(value: str) -> None:
    raise PublicReportOutputError(f"public report contains non-finite value: {value}")


def _validate_public_value(
    value: Any,
    *,
    path: str,
    depth: int,
    item_count: list[int],
) -> None:
    if depth > MAX_PUBLIC_REPORT_DEPTH:
        raise PublicReportOutputError("public report exceeds nesting limit")
    item_count[0] += 1
    if item_count[0] > MAX_PUBLIC_REPORT_ITEMS:
        raise PublicReportOutputError("public report exceeds item limit")

    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise PublicReportOutputError("public report object key must be text")
            normalized_key = key.casefold()
            if normalized_key in _SECRET_FIELD_NAMES:
                raise PublicReportOutputError(
                    f"public report contains sensitive field at {path}.{key}"
                )
            if (
                normalized_key in _CONDITIONAL_RAW_FIELD_NAMES
                and not _is_safe_omission_value(child)
            ):
                raise PublicReportOutputError(
                    f"public report contains raw field at {path}.{key}"
                )
            _validate_public_value(
                child,
                path=f"{path}.{key}",
                depth=depth + 1,
                item_count=item_count,
            )
        return

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _validate_public_value(
                child,
                path=f"{path}[{index}]",
                depth=depth + 1,
                item_count=item_count,
            )
        return

    if isinstance(value, str):
        _validate_public_string(value, path)
        return
    if isinstance(value, float) and not math.isfinite(value):
        raise PublicReportOutputError(f"public report contains non-finite number at {path}")
    if isinstance(value, int) and not isinstance(value, bool) and value.bit_length() > 63:
        raise PublicReportOutputError(f"public report integer exceeds limit at {path}")
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise PublicReportOutputError(f"public report contains unsupported value at {path}")


def _validate_public_string(value: str, path: str) -> None:
    if len(value) > MAX_PUBLIC_REPORT_STRING_LENGTH:
        raise PublicReportOutputError(f"public report string exceeds limit at {path}")
    if "\x00" in value:
        raise PublicReportOutputError(f"public report contains NUL at {path}")
    if value.startswith(("/", "\\\\")) or _WINDOWS_ABSOLUTE_PATH.match(value):
        raise PublicReportOutputError(f"public report contains absolute path at {path}")
    if any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS):
        raise PublicReportOutputError(f"public report contains secret material at {path}")


def _is_safe_omission_value(value: Any) -> bool:
    if value is False or value is None:
        return True
    return isinstance(value, str) and value in _SAFE_OMISSION_VALUES


__all__ = [
    "MAX_PUBLIC_REPORT_BYTES",
    "MAX_PUBLIC_REPORT_DEPTH",
    "MAX_PUBLIC_REPORT_ITEMS",
    "MAX_PUBLIC_REPORT_LINES",
    "MAX_PUBLIC_REPORT_LINE_LENGTH",
    "MAX_PUBLIC_REPORT_STRING_LENGTH",
    "PublicReportOutputError",
    "emit_public_json_report",
    "emit_public_text_report",
]
