"""Emit Source Ingestion Sandbox Implementation evidence."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

from examples.bounded_source_buffer_api import (
    BOUNDED_SOURCE_BUFFER_API_EVIDENCE_ID,
    build_bounded_source_buffer_api_report,
)
from tuc.frontend import (
    BOUNDED_SOURCE_BUFFER_API_CONTRACT,
    BOUNDED_SOURCE_BUFFER_API_STATUS,
    MAX_TRITON_SOURCE_LINES,
    SOURCE_INGESTION_SANDBOX_ADMISSION_EFFECT,
    SOURCE_INGESTION_SANDBOX_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INGESTION_SANDBOX_BLOCKED_OUTPUTS,
    SOURCE_INGESTION_SANDBOX_DIAGNOSTIC_POLICY,
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT,
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS,
    SOURCE_INGESTION_SANDBOX_OUTPUT_POLICY,
    SOURCE_INGESTION_SANDBOX_RAW_SOURCE_POLICY,
    SOURCE_INGESTION_SANDBOX_REJECTION_REASONS,
    SOURCE_INGESTION_SANDBOX_REQUIRED_CONTROLS,
    run_source_ingestion_sandbox,
    source_ingestion_sandbox_result_to_dict,
)

SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_REPORT_SCHEMA_VERSION = (
    "tuc.source_ingestion_sandbox_implementation_report.v0"
)
SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_EVIDENCE_ID = (
    "source_ingestion_sandbox_implementation"
)
SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_ARTIFACT_POLICY = (
    "metadata_only_source_free"
)
SOURCE_INGESTION_SANDBOX_ACCEPTED_CASES = (
    (
        "sandbox_accepts_module_metadata",
        "def kernel(x):\n    y = x + 1\n    return y\n",
        {"x": (4, 8), "y": (4, 8)},
    ),
    (
        "sandbox_accepts_decorator_as_data",
        "@triton.jit\ndef kernel(a, b):\n    c = a + b\n    return c\n",
        {"a": (8, 8), "b": (8, 8), "c": (8, 8)},
    ),
)
SOURCE_INGESTION_SANDBOX_REJECTION_CASES = (
    ("sandbox_rejects_empty_source", "", {"x": (1,)}, "empty_source"),
    (
        "sandbox_rejects_line_budget",
        "\n".join("x = 1" for _ in range(MAX_TRITON_SOURCE_LINES + 1)),
        {"x": (1,)},
        "line_budget",
    ),
    (
        "sandbox_rejects_syntax_error",
        "def broken(:\n    pass\n",
        {"x": (1,)},
        "syntax_error",
    ),
    (
        "sandbox_rejects_shape_profile",
        "x = 1\n",
        {"x": (True,)},
        "shape_profile",
    ),
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "accepted_case_count",
        "accepted_results",
        "admission_effect",
        "artifact_policy",
        "blocked_execution_surfaces",
        "blocked_outputs",
        "bounded_source_buffer_api_evidence",
        "diagnostic_policy",
        "direct_source_ingestion",
        "evidence_id",
        "issues",
        "output_policy",
        "raw_source_policy",
        "rejection_case_count",
        "rejection_results",
        "report_digest",
        "required_control_count",
        "required_controls",
        "sandbox_contract",
        "sandbox_status",
        "schema_version",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_intent_plain_data",
        "source_to_runtime_plan",
    }
)
_ACCEPTED_RESULT_KEYS = frozenset(
    {
        "admission_effect",
        "ast_depth",
        "ast_node_count",
        "blocked_execution_surfaces",
        "blocked_outputs",
        "bounded_source_buffer_api_contract",
        "bounded_source_buffer_api_status",
        "bounded_source_buffer_record_digest",
        "diagnostic_policy",
        "direct_source_ingestion",
        "line_count",
        "outcome",
        "output_policy",
        "raw_source_policy",
        "reason_code",
        "sandbox_contract",
        "sandbox_status",
        "shape_profile_digest",
        "shape_profile_entry_count",
        "shape_profile_max_rank",
        "source_bytes",
        "source_digest",
        "source_name",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_intent_plain_data",
        "source_to_runtime_plan",
    }
)
_REJECTION_RESULT_KEYS = frozenset(
    {
        "admission_effect",
        "blocked_execution_surfaces",
        "blocked_outputs",
        "diagnostic_policy",
        "direct_source_ingestion",
        "outcome",
        "output_policy",
        "raw_source_policy",
        "reason_code",
        "sandbox_contract",
        "sandbox_status",
        "source_digest",
        "source_free",
        "source_name",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_intent_plain_data",
        "source_to_runtime_plan",
    }
)
_BOUND_EVIDENCE_KEYS = frozenset(
    {"contract", "digest", "evidence_id", "source_free", "status", "supports_sandbox"}
)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    "tl.dot",
    '"backend_artifact_path":',
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


class SourceIngestionSandboxImplementationReportError(AssertionError):
    """Raised when Source Ingestion Sandbox Implementation evidence drifts."""


def build_source_ingestion_sandbox_implementation_report() -> dict[str, object]:
    """Build the current source-free sandbox implementation report."""

    accepted_results = [
        source_ingestion_sandbox_result_to_dict(
            run_source_ingestion_sandbox(
                source,
                source_name=case_id,
                declared_shape_profile=shape_profile,
            )
        )
        for case_id, source, shape_profile in SOURCE_INGESTION_SANDBOX_ACCEPTED_CASES
    ]
    rejection_results = [
        _build_rejection_result(case_id, source, shape_profile, reason_code)
        for case_id, source, shape_profile, reason_code in (
            SOURCE_INGESTION_SANDBOX_REJECTION_CASES
        )
    ]
    bounded_source_buffer_report = build_bounded_source_buffer_api_report()
    report: dict[str, object] = {
        "accepted_case_count": len(accepted_results),
        "accepted_results": accepted_results,
        "admission_effect": SOURCE_INGESTION_SANDBOX_ADMISSION_EFFECT,
        "artifact_policy": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_ARTIFACT_POLICY,
        "blocked_execution_surfaces": list(
            SOURCE_INGESTION_SANDBOX_BLOCKED_EXECUTION_SURFACES
        ),
        "blocked_outputs": list(SOURCE_INGESTION_SANDBOX_BLOCKED_OUTPUTS),
        "bounded_source_buffer_api_evidence": {
            "contract": BOUNDED_SOURCE_BUFFER_API_CONTRACT,
            "digest": _digest_payload(bounded_source_buffer_report),
            "evidence_id": BOUNDED_SOURCE_BUFFER_API_EVIDENCE_ID,
            "source_free": True,
            "status": BOUNDED_SOURCE_BUFFER_API_STATUS,
            "supports_sandbox": True,
        },
        "diagnostic_policy": SOURCE_INGESTION_SANDBOX_DIAGNOSTIC_POLICY,
        "direct_source_ingestion": False,
        "evidence_id": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_EVIDENCE_ID,
        "issues": [],
        "output_policy": SOURCE_INGESTION_SANDBOX_OUTPUT_POLICY,
        "raw_source_policy": SOURCE_INGESTION_SANDBOX_RAW_SOURCE_POLICY,
        "rejection_case_count": len(rejection_results),
        "rejection_results": rejection_results,
        "required_control_count": len(SOURCE_INGESTION_SANDBOX_REQUIRED_CONTROLS),
        "required_controls": list(SOURCE_INGESTION_SANDBOX_REQUIRED_CONTROLS),
        "sandbox_contract": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT,
        "sandbox_status": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS,
        "schema_version": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_REPORT_SCHEMA_VERSION,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_intent_plain_data": False,
        "source_to_runtime_plan": False,
    }
    report["report_digest"] = _digest_payload(report)
    assert_source_ingestion_sandbox_implementation_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the sandbox implementation."""

    return json.dumps(
        build_source_ingestion_sandbox_implementation_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_source_ingestion_sandbox_implementation_report_contract(
    report: object,
) -> None:
    """Fail closed unless the sandbox implementation report matches v0."""

    if not isinstance(report, Mapping):
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox report must be object"
        )
    if set(report) != _TOP_LEVEL_KEYS:
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox top-level keys drift"
        )
    expected = {
        "accepted_case_count": len(SOURCE_INGESTION_SANDBOX_ACCEPTED_CASES),
        "admission_effect": SOURCE_INGESTION_SANDBOX_ADMISSION_EFFECT,
        "artifact_policy": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_ARTIFACT_POLICY,
        "diagnostic_policy": SOURCE_INGESTION_SANDBOX_DIAGNOSTIC_POLICY,
        "direct_source_ingestion": False,
        "evidence_id": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_EVIDENCE_ID,
        "output_policy": SOURCE_INGESTION_SANDBOX_OUTPUT_POLICY,
        "raw_source_policy": SOURCE_INGESTION_SANDBOX_RAW_SOURCE_POLICY,
        "rejection_case_count": len(SOURCE_INGESTION_SANDBOX_REJECTION_CASES),
        "required_control_count": len(SOURCE_INGESTION_SANDBOX_REQUIRED_CONTROLS),
        "sandbox_contract": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT,
        "sandbox_status": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS,
        "schema_version": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_REPORT_SCHEMA_VERSION,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_intent_plain_data": False,
        "source_to_runtime_plan": False,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise SourceIngestionSandboxImplementationReportError(
                f"source sandbox {key} drift"
            )
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        SOURCE_INGESTION_SANDBOX_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("blocked_outputs"),
        SOURCE_INGESTION_SANDBOX_BLOCKED_OUTPUTS,
        "blocked_outputs",
    )
    _assert_string_sequence(
        report.get("required_controls"),
        SOURCE_INGESTION_SANDBOX_REQUIRED_CONTROLS,
        "required_controls",
    )
    _assert_bounded_source_buffer_api_evidence(
        report.get("bounded_source_buffer_api_evidence")
    )
    _assert_accepted_results(report.get("accepted_results"))
    _assert_rejection_results(report.get("rejection_results"))
    if report.get("issues") != []:
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox issues must be empty"
        )
    digest = report.get("report_digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox digest invalid"
        )
    if digest != _digest_payload(report):
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox digest drift"
        )
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_rejection_result(
    case_id: str,
    source: str,
    shape_profile: Mapping[str, object],
    reason_code: str,
) -> dict[str, object]:
    result = run_source_ingestion_sandbox(
        source,
        source_name=case_id,
        declared_shape_profile=shape_profile,  # type: ignore[arg-type]
    )
    payload = source_ingestion_sandbox_result_to_dict(result)
    if payload.get("outcome") != "rejected":
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox rejection case accepted"
        )
    if payload.get("reason_code") != reason_code:
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox rejection reason drift"
        )
    return payload


def _assert_bounded_source_buffer_api_evidence(value: object) -> None:
    if not isinstance(value, Mapping) or set(value) != _BOUND_EVIDENCE_KEYS:
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox bounded evidence keys drift"
        )
    expected = {
        "contract": BOUNDED_SOURCE_BUFFER_API_CONTRACT,
        "evidence_id": BOUNDED_SOURCE_BUFFER_API_EVIDENCE_ID,
        "source_free": True,
        "status": BOUNDED_SOURCE_BUFFER_API_STATUS,
        "supports_sandbox": True,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise SourceIngestionSandboxImplementationReportError(
                "source sandbox bounded evidence drift"
            )
    digest = value.get("digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox bounded digest invalid"
        )


def _assert_accepted_results(value: object) -> None:
    if not isinstance(value, list):
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox accepted results must be list"
        )
    if len(value) != len(SOURCE_INGESTION_SANDBOX_ACCEPTED_CASES):
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox accepted count drift"
        )
    names = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _ACCEPTED_RESULT_KEYS:
            raise SourceIngestionSandboxImplementationReportError(
                "source sandbox accepted result keys drift"
            )
        names.append(item.get("source_name"))
        if item.get("outcome") != "accepted_metadata_only":
            raise SourceIngestionSandboxImplementationReportError(
                "source sandbox accepted outcome drift"
            )
        if item.get("reason_code") != "accepted_metadata_only":
            raise SourceIngestionSandboxImplementationReportError(
                "source sandbox accepted reason drift"
            )
        if item.get("source_to_intent_plain_data") is not False:
            raise SourceIngestionSandboxImplementationReportError(
                "source sandbox Source Intent output drift"
            )
        _assert_result_common(item)
        for key in (
            "bounded_source_buffer_record_digest",
            "shape_profile_digest",
            "source_digest",
        ):
            digest = item.get(key)
            if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                raise SourceIngestionSandboxImplementationReportError(
                    "source sandbox accepted digest invalid"
                )
    if tuple(names) != tuple(case[0] for case in SOURCE_INGESTION_SANDBOX_ACCEPTED_CASES):
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox accepted names drift"
        )


def _assert_rejection_results(value: object) -> None:
    if not isinstance(value, list):
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox rejection results must be list"
        )
    if len(value) != len(SOURCE_INGESTION_SANDBOX_REJECTION_CASES):
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox rejection count drift"
        )
    observed: list[tuple[object, object]] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _REJECTION_RESULT_KEYS:
            raise SourceIngestionSandboxImplementationReportError(
                "source sandbox rejection result keys drift"
            )
        if item.get("outcome") != "rejected" or item.get("source_free") is not True:
            raise SourceIngestionSandboxImplementationReportError(
                "source sandbox rejection outcome drift"
            )
        if item.get("reason_code") not in SOURCE_INGESTION_SANDBOX_REJECTION_REASONS:
            raise SourceIngestionSandboxImplementationReportError(
                "source sandbox rejection reason invalid"
            )
        _assert_result_common(item)
        digest = item.get("source_digest")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise SourceIngestionSandboxImplementationReportError(
                "source sandbox rejection digest invalid"
            )
        observed.append((item.get("source_name"), item.get("reason_code")))
    if tuple(observed) != tuple(
        (case_id, reason_code)
        for case_id, _source, _shape_profile, reason_code in (
            SOURCE_INGESTION_SANDBOX_REJECTION_CASES
        )
    ):
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox rejection cases drift"
        )


def _assert_result_common(item: Mapping[str, object]) -> None:
    expected = {
        "admission_effect": SOURCE_INGESTION_SANDBOX_ADMISSION_EFFECT,
        "blocked_execution_surfaces": list(
            SOURCE_INGESTION_SANDBOX_BLOCKED_EXECUTION_SURFACES
        ),
        "blocked_outputs": list(SOURCE_INGESTION_SANDBOX_BLOCKED_OUTPUTS),
        "diagnostic_policy": SOURCE_INGESTION_SANDBOX_DIAGNOSTIC_POLICY,
        "direct_source_ingestion": False,
        "output_policy": SOURCE_INGESTION_SANDBOX_OUTPUT_POLICY,
        "raw_source_policy": SOURCE_INGESTION_SANDBOX_RAW_SOURCE_POLICY,
        "sandbox_contract": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT,
        "sandbox_status": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_intent_plain_data": False,
        "source_to_runtime_plan": False,
    }
    for key, expected_value in expected.items():
        if item.get(key) != expected_value:
            raise SourceIngestionSandboxImplementationReportError(
                f"source sandbox result {key} drift"
            )
    source_name = item.get("source_name")
    if not isinstance(source_name, str) or not _REPORT_TEXT_RE.fullmatch(source_name):
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox result source_name invalid"
        )


def _assert_string_sequence(value: object, expected: tuple[str, ...], field: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise SourceIngestionSandboxImplementationReportError(
            f"source sandbox {field} drift"
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise SourceIngestionSandboxImplementationReportError(
            "source sandbox expected string list"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise SourceIngestionSandboxImplementationReportError(
                "source sandbox string list item invalid"
            )
        if not _REPORT_TEXT_RE.fullmatch(item):
            raise SourceIngestionSandboxImplementationReportError(
                "source sandbox string list item unsafe"
            )
        result.append(item)
    return result


def _digest_payload(payload: Mapping[str, object]) -> str:
    value = dict(payload)
    value.pop("report_digest", None)
    text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise SourceIngestionSandboxImplementationReportError(
                f"source sandbox report contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()