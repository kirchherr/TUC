"""Emit Bounded Source Buffer API evidence."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

from tuc.frontend import (
    BOUNDED_SOURCE_BUFFER_ADMISSION_EFFECT,
    BOUNDED_SOURCE_BUFFER_API_CONTRACT,
    BOUNDED_SOURCE_BUFFER_API_STATUS,
    BOUNDED_SOURCE_BUFFER_BLOCKED_EXECUTION_SURFACES,
    BOUNDED_SOURCE_BUFFER_BLOCKED_OUTPUTS,
    BOUNDED_SOURCE_BUFFER_DIAGNOSTIC_POLICY,
    BOUNDED_SOURCE_BUFFER_OUTPUT_POLICY,
    BOUNDED_SOURCE_BUFFER_RAW_SOURCE_POLICY,
    MAX_BOUNDED_SOURCE_BUFFER_SHAPE_PROFILE_ENTRIES,
    MAX_SOURCE_INTENT_DIMENSION,
    MAX_SOURCE_INTENT_RANK,
    MAX_TRITON_SOURCE_AST_DEPTH,
    MAX_TRITON_SOURCE_AST_NODES,
    MAX_TRITON_SOURCE_BYTES,
    MAX_TRITON_SOURCE_LINES,
    BoundedSourceBufferError,
    bound_source_buffer,
    bounded_source_buffer_record_to_dict,
)

BOUNDED_SOURCE_BUFFER_API_REPORT_SCHEMA_VERSION = (
    "tuc.bounded_source_buffer_api_report.v0"
)
BOUNDED_SOURCE_BUFFER_API_EVIDENCE_ID = "bounded_source_buffer_api"
BOUNDED_SOURCE_BUFFER_API_ARTIFACT_POLICY = "metadata_only_source_free"
BOUNDED_SOURCE_BUFFER_API_REQUIRED_CONTROLS = (
    "bounded_source_buffer",
    "utf8_decode_before_validation",
    "source_buffer_size_limit",
    "source_line_limit",
    "ast_node_limit",
    "ast_depth_limit",
    "declared_shape_profile_required",
    "shape_profile_entry_limit",
    "shape_rank_limit",
    "shape_dimension_limit",
    "source_digest_only",
    "source_free_diagnostics",
    "no_source_to_intent_output",
    "no_compiler_artifact_output",
)
BOUNDED_SOURCE_BUFFER_API_ACCEPTED_CASES = (
    (
        "accepted_module_buffer",
        "def kernel(x):\n    y = x + 1\n    return y\n",
        {"x": (4, 8), "y": (4, 8)},
    ),
    (
        "accepted_decorator_data_buffer",
        "@triton.jit\ndef kernel(a, b):\n    c = a + b\n    return c\n",
        {"a": (8, 8), "b": (8, 8), "c": (8, 8)},
    ),
)
BOUNDED_SOURCE_BUFFER_API_REJECTION_CASES = (
    ("empty_source_buffer", "", {"x": (1,)}, "empty_source"),
    (
        "source_line_budget",
        "\n".join("x = 1" for _ in range(MAX_TRITON_SOURCE_LINES + 1)),
        {"x": (1,)},
        "line_budget",
    ),
    ("syntax_error", "def broken(:\n    pass\n", {"x": (1,)}, "syntax_error"),
    ("invalid_shape_profile", "x = 1\n", {"x": (True,)}, "shape_profile"),
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "accepted_case_count",
        "accepted_records",
        "admission_effect",
        "api_contract",
        "api_status",
        "artifact_policy",
        "blocked_execution_surfaces",
        "blocked_outputs",
        "budget_limits",
        "diagnostic_policy",
        "direct_source_ingestion",
        "evidence_id",
        "issues",
        "output_policy",
        "raw_source_policy",
        "rejection_case_count",
        "rejection_cases",
        "report_digest",
        "required_control_count",
        "required_controls",
        "schema_version",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_runtime_plan",
    }
)
_RECORD_KEYS = frozenset(
    {
        "admission_effect",
        "api_contract",
        "api_status",
        "ast_depth",
        "ast_node_count",
        "blocked_execution_surfaces",
        "blocked_outputs",
        "diagnostic_policy",
        "line_count",
        "output_policy",
        "raw_source_policy",
        "shape_profile_digest",
        "shape_profile_entry_count",
        "shape_profile_max_rank",
        "source_bytes",
        "source_digest",
        "source_name",
    }
)
_REJECTION_KEYS = frozenset(
    {"case_id", "outcome", "reason_code", "source_digest", "source_free"}
)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    "tl.dot",
    '"command_line":',
    '"device_id":',
    '"file_path":',
    '"generated_code":',
    '"host_path":',
    '"plugin_entrypoint":',
    '"python_source":',
    '"raw_source":',
    '"raw_source_text":',
    '"raw_tensor_value":',
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_text":',
)


class BoundedSourceBufferAPIReportError(AssertionError):
    """Raised when Bounded Source Buffer API evidence drifts."""


def build_bounded_source_buffer_api_report() -> dict[str, object]:
    """Build the current source-free Bounded Source Buffer API report."""

    accepted_records = [
        bounded_source_buffer_record_to_dict(
            bound_source_buffer(
                source,
                source_name=case_id,
                declared_shape_profile=shape_profile,
            )
        )
        for case_id, source, shape_profile in BOUNDED_SOURCE_BUFFER_API_ACCEPTED_CASES
    ]
    rejection_cases = [
        _build_rejection_case(case_id, source, shape_profile, reason_code)
        for case_id, source, shape_profile, reason_code in (
            BOUNDED_SOURCE_BUFFER_API_REJECTION_CASES
        )
    ]
    report: dict[str, object] = {
        "accepted_case_count": len(accepted_records),
        "accepted_records": accepted_records,
        "admission_effect": BOUNDED_SOURCE_BUFFER_ADMISSION_EFFECT,
        "api_contract": BOUNDED_SOURCE_BUFFER_API_CONTRACT,
        "api_status": BOUNDED_SOURCE_BUFFER_API_STATUS,
        "artifact_policy": BOUNDED_SOURCE_BUFFER_API_ARTIFACT_POLICY,
        "blocked_execution_surfaces": list(
            BOUNDED_SOURCE_BUFFER_BLOCKED_EXECUTION_SURFACES
        ),
        "blocked_outputs": list(BOUNDED_SOURCE_BUFFER_BLOCKED_OUTPUTS),
        "budget_limits": {
            "ast_depth": MAX_TRITON_SOURCE_AST_DEPTH,
            "ast_nodes": MAX_TRITON_SOURCE_AST_NODES,
            "shape_dimension": MAX_SOURCE_INTENT_DIMENSION,
            "shape_profile_entries": MAX_BOUNDED_SOURCE_BUFFER_SHAPE_PROFILE_ENTRIES,
            "shape_rank": MAX_SOURCE_INTENT_RANK,
            "source_bytes": MAX_TRITON_SOURCE_BYTES,
            "source_lines": MAX_TRITON_SOURCE_LINES,
        },
        "diagnostic_policy": BOUNDED_SOURCE_BUFFER_DIAGNOSTIC_POLICY,
        "direct_source_ingestion": False,
        "evidence_id": BOUNDED_SOURCE_BUFFER_API_EVIDENCE_ID,
        "issues": [],
        "output_policy": BOUNDED_SOURCE_BUFFER_OUTPUT_POLICY,
        "raw_source_policy": BOUNDED_SOURCE_BUFFER_RAW_SOURCE_POLICY,
        "rejection_case_count": len(rejection_cases),
        "rejection_cases": rejection_cases,
        "required_control_count": len(BOUNDED_SOURCE_BUFFER_API_REQUIRED_CONTROLS),
        "required_controls": list(BOUNDED_SOURCE_BUFFER_API_REQUIRED_CONTROLS),
        "schema_version": BOUNDED_SOURCE_BUFFER_API_REPORT_SCHEMA_VERSION,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
    }
    report["report_digest"] = _digest_payload(report)
    assert_bounded_source_buffer_api_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the Bounded Source Buffer API."""

    return json.dumps(
        build_bounded_source_buffer_api_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_bounded_source_buffer_api_report_contract(report: object) -> None:
    """Fail closed unless the Bounded Source Buffer API report matches v0."""

    if not isinstance(report, Mapping):
        raise BoundedSourceBufferAPIReportError("bounded source report must be object")
    if set(report) != _TOP_LEVEL_KEYS:
        raise BoundedSourceBufferAPIReportError("bounded source top-level keys drift")
    expected = {
        "accepted_case_count": len(BOUNDED_SOURCE_BUFFER_API_ACCEPTED_CASES),
        "admission_effect": BOUNDED_SOURCE_BUFFER_ADMISSION_EFFECT,
        "api_contract": BOUNDED_SOURCE_BUFFER_API_CONTRACT,
        "api_status": BOUNDED_SOURCE_BUFFER_API_STATUS,
        "artifact_policy": BOUNDED_SOURCE_BUFFER_API_ARTIFACT_POLICY,
        "diagnostic_policy": BOUNDED_SOURCE_BUFFER_DIAGNOSTIC_POLICY,
        "direct_source_ingestion": False,
        "evidence_id": BOUNDED_SOURCE_BUFFER_API_EVIDENCE_ID,
        "output_policy": BOUNDED_SOURCE_BUFFER_OUTPUT_POLICY,
        "raw_source_policy": BOUNDED_SOURCE_BUFFER_RAW_SOURCE_POLICY,
        "rejection_case_count": len(BOUNDED_SOURCE_BUFFER_API_REJECTION_CASES),
        "required_control_count": len(BOUNDED_SOURCE_BUFFER_API_REQUIRED_CONTROLS),
        "schema_version": BOUNDED_SOURCE_BUFFER_API_REPORT_SCHEMA_VERSION,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise BoundedSourceBufferAPIReportError(f"bounded source {key} drift")
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        BOUNDED_SOURCE_BUFFER_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("blocked_outputs"),
        BOUNDED_SOURCE_BUFFER_BLOCKED_OUTPUTS,
        "blocked_outputs",
    )
    _assert_string_sequence(
        report.get("required_controls"),
        BOUNDED_SOURCE_BUFFER_API_REQUIRED_CONTROLS,
        "required_controls",
    )
    _assert_budget_limits(report.get("budget_limits"))
    _assert_accepted_records(report.get("accepted_records"))
    _assert_rejection_cases(report.get("rejection_cases"))
    if report.get("issues") != []:
        raise BoundedSourceBufferAPIReportError("bounded source issues must be empty")
    digest = report.get("report_digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise BoundedSourceBufferAPIReportError("bounded source digest invalid")
    if digest != _digest_payload(report):
        raise BoundedSourceBufferAPIReportError("bounded source digest drift")
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_rejection_case(
    case_id: str,
    source: str,
    shape_profile: Mapping[str, object],
    reason_code: str,
) -> dict[str, object]:
    try:
        bound_source_buffer(
            source,
            source_name=case_id,
            declared_shape_profile=shape_profile,  # type: ignore[arg-type]
        )
    except (BoundedSourceBufferError, TypeError):
        return {
            "case_id": case_id,
            "outcome": "rejected",
            "reason_code": reason_code,
            "source_digest": _digest_text(source),
            "source_free": True,
        }
    raise BoundedSourceBufferAPIReportError("bounded source rejection case accepted")


def _assert_budget_limits(value: object) -> None:
    if value != {
        "ast_depth": MAX_TRITON_SOURCE_AST_DEPTH,
        "ast_nodes": MAX_TRITON_SOURCE_AST_NODES,
        "shape_dimension": MAX_SOURCE_INTENT_DIMENSION,
        "shape_profile_entries": MAX_BOUNDED_SOURCE_BUFFER_SHAPE_PROFILE_ENTRIES,
        "shape_rank": MAX_SOURCE_INTENT_RANK,
        "source_bytes": MAX_TRITON_SOURCE_BYTES,
        "source_lines": MAX_TRITON_SOURCE_LINES,
    }:
        raise BoundedSourceBufferAPIReportError("bounded source budget limits drift")


def _assert_accepted_records(value: object) -> None:
    if not isinstance(value, list):
        raise BoundedSourceBufferAPIReportError("bounded source records must be list")
    if len(value) != len(BOUNDED_SOURCE_BUFFER_API_ACCEPTED_CASES):
        raise BoundedSourceBufferAPIReportError("bounded source record count drift")
    names = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _RECORD_KEYS:
            raise BoundedSourceBufferAPIReportError("bounded source record keys drift")
        names.append(item.get("source_name"))
        for key in ("source_digest", "shape_profile_digest"):
            digest = item.get(key)
            if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                raise BoundedSourceBufferAPIReportError(
                    "bounded source record digest invalid"
                )
        if item.get("api_status") != BOUNDED_SOURCE_BUFFER_API_STATUS:
            raise BoundedSourceBufferAPIReportError("bounded source record status drift")
        if item.get("raw_source_policy") != BOUNDED_SOURCE_BUFFER_RAW_SOURCE_POLICY:
            raise BoundedSourceBufferAPIReportError("bounded source raw policy drift")
    if tuple(names) != tuple(case[0] for case in BOUNDED_SOURCE_BUFFER_API_ACCEPTED_CASES):
        raise BoundedSourceBufferAPIReportError("bounded source record names drift")


def _assert_rejection_cases(value: object) -> None:
    if not isinstance(value, list):
        raise BoundedSourceBufferAPIReportError("bounded source rejections must be list")
    if len(value) != len(BOUNDED_SOURCE_BUFFER_API_REJECTION_CASES):
        raise BoundedSourceBufferAPIReportError("bounded source rejection count drift")
    observed: list[tuple[object, object]] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _REJECTION_KEYS:
            raise BoundedSourceBufferAPIReportError("bounded source rejection keys drift")
        if item.get("outcome") != "rejected" or item.get("source_free") is not True:
            raise BoundedSourceBufferAPIReportError("bounded source rejection drift")
        digest = item.get("source_digest")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise BoundedSourceBufferAPIReportError("bounded source rejection digest drift")
        observed.append((item.get("case_id"), item.get("reason_code")))
    if tuple(observed) != tuple(
        (case_id, reason_code)
        for case_id, _source, _shape_profile, reason_code in (
            BOUNDED_SOURCE_BUFFER_API_REJECTION_CASES
        )
    ):
        raise BoundedSourceBufferAPIReportError("bounded source rejection cases drift")


def _assert_string_sequence(value: object, expected: tuple[str, ...], field: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise BoundedSourceBufferAPIReportError(f"bounded source {field} drift")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise BoundedSourceBufferAPIReportError("bounded source expected string list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise BoundedSourceBufferAPIReportError("bounded source list item invalid")
        if not _REPORT_TEXT_RE.fullmatch(item):
            raise BoundedSourceBufferAPIReportError("bounded source list item unsafe")
        result.append(item)
    return result


def _digest_payload(payload: Mapping[str, object]) -> str:
    value = dict(payload)
    value.pop("report_digest", None)
    text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return _digest_text(text)


def _digest_text(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise BoundedSourceBufferAPIReportError(
                f"bounded source report contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
