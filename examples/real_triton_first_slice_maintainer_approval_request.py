"""Emit the Real Triton first-slice maintainer approval request packet."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_SCHEMA_VERSION = (
    "tuc.real_triton_first_slice_maintainer_approval_request_report.v0"
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_CONTRACT = (
    "real_triton_first_slice_maintainer_approval_request.data_only.v0"
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_ID = (
    "real_triton_first_slice_maintainer_approval_request"
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_STATUS = (
    "ready_for_external_review"
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_APPROVAL_STATUS = "not_approved"
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_DECISION = (
    "request_external_review_keep_blocked"
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_SCOPE = (
    "external_maintainer_security_review_only"
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_TARGET_SURFACE = (
    "direct_source_ingestion"
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_TARGET_SLICE = (
    "bounded_source_buffer_to_source_intent_plain_data"
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_POLICY = (
    "digest_only_fixed_artifact_request"
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EXTERNAL_EVIDENCE = (
    "maintainer_security_review_approval",
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REVIEW_CHECKLIST = (
    "admission_readiness_gate_reviewed",
    "maintainer_security_review_packet_reviewed",
    "approval_artifact_absence_reviewed",
    "source_ingestion_admission_gate_reviewed",
    "bounded_source_buffer_reviewed",
    "sandbox_boundary_reviewed",
    "negative_corpus_reviewed",
    "source_free_diagnostics_reviewed",
    "plain_data_golden_reviewed",
    "ci_replay_reviewed",
    "no_source_text_serialization",
    "no_runtime_handle_serialization",
    "no_generated_artifact_execution",
    "direct_source_ingestion_remains_blocked_until_approval",
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_BLOCKED_CLAIMS = (
    "arbitrary_triton_source_ingestion",
    "production_parser",
    "source_to_compute_graph_admission",
    "native_backend_execution",
    "native_performance_parity",
    "vendor_replacement",
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_BLOCKED_EXECUTION_SURFACES = (
    "direct_source_ingestion",
    "source_to_compute_graph",
    "source_to_hac_ir",
    "source_to_runtime_plan",
    "frontend_package_import",
    "plugin_discovery",
    "triton_jit_execution",
    "device_access",
    "generated_artifact_execution",
    "native_backend_execution",
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REQUIRED_INVARIANTS = (
    "approval_request_is_not_approval",
    "external_approval_required",
    "external_approval_artifact_absent",
    "admission_readiness_gate_bound",
    "admission_readiness_gate_fail_closed",
    "maintainer_review_packet_ready",
    "source_ingestion_admission_gate_fail_closed",
    "direct_source_ingestion_false",
    "source_to_compute_graph_false",
    "source_to_hac_ir_false",
    "source_to_runtime_plan_false",
    "surface_opened_false",
    "digest_only_source_free_evidence",
)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]

_EVIDENCE_SPECS = (
    {
        "artifact_id": "real_triton_first_slice_admission_readiness_gate",
        "relative_path": Path(
            "tests/golden/frontend/real_triton_first_slice_admission_readiness_gate_report.json"
        ),
        "contract_key": "gate_contract",
        "status_key": "gate_status",
        "expected_contract": "real_triton_first_slice_admission_readiness_gate.data_only.v0",
        "expected_status": "blocked_missing_maintainer_security_review_approval",
    },
    {
        "artifact_id": "source_ingestion_maintainer_security_review_packet",
        "relative_path": Path(
            "tests/golden/frontend/source_ingestion_maintainer_security_review_packet_report.json"
        ),
        "contract_key": "contract",
        "status_key": "status",
        "expected_contract": "source_ingestion_maintainer_security_review_packet.review.v0",
        "expected_status": "ready_for_maintainer_review",
    },
    {
        "artifact_id": "source_ingestion_maintainer_approval_artifact",
        "relative_path": Path(
            "tests/golden/frontend/source_ingestion_maintainer_approval_artifact_report.json"
        ),
        "contract_key": "contract",
        "status_key": "status",
        "expected_contract": "source_ingestion_maintainer_approval_artifact.absent.v0",
        "expected_status": "external_approval_not_supplied",
    },
    {
        "artifact_id": "source_ingestion_admission_gate",
        "relative_path": Path("tests/golden/frontend/source_ingestion_admission_gate_report.json"),
        "contract_key": "gate_contract",
        "status_key": "gate_status",
        "expected_contract": "source_ingestion_admission_gate.fail_closed.v0",
        "expected_status": "blocked_missing_maintainer_security_review_approval",
    },
)
REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_IDS = tuple(
    str(spec["artifact_id"]) for spec in _EVIDENCE_SPECS
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "admission_decision",
        "admission_ready",
        "admitted",
        "approval_artifact_present",
        "approval_request_is_approval",
        "approval_request_scope",
        "approval_status",
        "blocked_claims",
        "blocked_execution_surfaces",
        "direct_source_ingestion",
        "evidence_policy",
        "external_approval_evidence",
        "external_approval_evidence_count",
        "external_approval_required",
        "issues",
        "request_contract",
        "request_id",
        "request_status",
        "required_invariants",
        "review_checklist",
        "review_checklist_count",
        "review_packet_count",
        "review_packets",
        "schema_version",
        "source_free",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_runtime_plan",
        "surface_opened",
        "target_slice",
        "target_surface",
    }
)
_EVIDENCE_KEYS = frozenset(
    {
        "artifact_id",
        "contract",
        "digest",
        "source_free",
        "status",
        "supports_approval_request",
    }
)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    '"backend_artifact":',
    '"command_line":',
    '"device_id":',
    '"file_path":',
    '"generated_code":',
    '"host_path":',
    "import os",
    "import triton",
    '"plugin_entrypoint":',
    '"python_source":',
    '"raw_source":',
    '"raw_source_text":',
    '"raw_tensor_value":',
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_text":',
    "tl.dot",
    "tl.store",
)


class RealTritonFirstSliceMaintainerApprovalRequestError(AssertionError):
    """Raised when the first-slice maintainer approval request drifts."""


def build_real_triton_first_slice_maintainer_approval_request_report(
    *,
    artifact_text_overrides: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Return the source-free external-review request for the first slice."""

    packets = tuple(_build_review_packet(spec, artifact_text_overrides) for spec in _EVIDENCE_SPECS)
    payloads = {
        str(spec["artifact_id"]): _payload_for_spec(spec, artifact_text_overrides)
        for spec in _EVIDENCE_SPECS
    }
    _assert_request_payloads(payloads)

    report: dict[str, object] = {
        "admission_decision": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_DECISION,
        "admission_ready": False,
        "admitted": False,
        "approval_artifact_present": False,
        "approval_request_is_approval": False,
        "approval_request_scope": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_SCOPE,
        "approval_status": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_APPROVAL_STATUS,
        "blocked_claims": list(
            REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_BLOCKED_CLAIMS
        ),
        "blocked_execution_surfaces": list(
            REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_BLOCKED_EXECUTION_SURFACES
        ),
        "direct_source_ingestion": False,
        "evidence_policy": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_POLICY,
        "external_approval_evidence": list(
            REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EXTERNAL_EVIDENCE
        ),
        "external_approval_evidence_count": len(
            REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EXTERNAL_EVIDENCE
        ),
        "external_approval_required": True,
        "issues": [],
        "request_contract": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_CONTRACT,
        "request_id": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_ID,
        "request_status": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_STATUS,
        "required_invariants": list(
            REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REQUIRED_INVARIANTS
        ),
        "review_checklist": list(
            REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REVIEW_CHECKLIST
        ),
        "review_checklist_count": len(
            REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REVIEW_CHECKLIST
        ),
        "review_packet_count": len(
            REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_IDS
        ),
        "review_packets": [dict(item) for item in packets],
        "schema_version": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_SCHEMA_VERSION,
        "source_free": True,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
        "surface_opened": False,
        "target_slice": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_TARGET_SLICE,
        "target_surface": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_TARGET_SURFACE,
    }
    assert_real_triton_first_slice_maintainer_approval_request_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the first-slice approval request."""

    return json.dumps(
        build_real_triton_first_slice_maintainer_approval_request_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_real_triton_first_slice_maintainer_approval_request_report_contract(
    report: object,
) -> None:
    """Fail closed unless the request packet matches the current v0 contract."""

    if not isinstance(report, Mapping):
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request must be object"
        )
    if set(report) != _TOP_LEVEL_KEYS:
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request top-level keys drift"
        )
    expected = {
        "admission_decision": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_DECISION,
        "admission_ready": False,
        "admitted": False,
        "approval_artifact_present": False,
        "approval_request_is_approval": False,
        "approval_request_scope": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_SCOPE,
        "approval_status": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_APPROVAL_STATUS,
        "direct_source_ingestion": False,
        "evidence_policy": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_POLICY,
        "external_approval_evidence_count": len(
            REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EXTERNAL_EVIDENCE
        ),
        "external_approval_required": True,
        "request_contract": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_CONTRACT,
        "request_id": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_ID,
        "request_status": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_STATUS,
        "review_checklist_count": len(
            REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REVIEW_CHECKLIST
        ),
        "review_packet_count": len(
            REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_IDS
        ),
        "schema_version": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_SCHEMA_VERSION,
        "source_free": True,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
        "surface_opened": False,
        "target_slice": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_TARGET_SLICE,
        "target_surface": REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_TARGET_SURFACE,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise RealTritonFirstSliceMaintainerApprovalRequestError(
                f"first-slice maintainer approval request {key} drift"
            )
    _assert_string_sequence(
        report.get("blocked_claims"),
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_BLOCKED_CLAIMS,
        "blocked_claims",
    )
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("external_approval_evidence"),
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EXTERNAL_EVIDENCE,
        "external_approval_evidence",
    )
    _assert_string_sequence(
        report.get("required_invariants"),
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REQUIRED_INVARIANTS,
        "required_invariants",
    )
    _assert_string_sequence(
        report.get("review_checklist"),
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_REVIEW_CHECKLIST,
        "review_checklist",
    )
    _assert_review_packets(report.get("review_packets"))
    if report.get("issues") != []:
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request issues must be empty"
        )
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_review_packet(
    spec: Mapping[str, object],
    artifact_text_overrides: Mapping[str, str] | None,
) -> Mapping[str, object]:
    payload = _payload_for_spec(spec, artifact_text_overrides)
    contract_key = str(spec["contract_key"])
    status_key = str(spec["status_key"])
    expected_contract = str(spec["expected_contract"])
    expected_status = str(spec["expected_status"])
    if payload.get(contract_key) != expected_contract or payload.get(status_key) != expected_status:
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request evidence status drift"
        )
    return {
        "artifact_id": str(spec["artifact_id"]),
        "contract": expected_contract,
        "digest": _digest(_text_for_spec(spec, artifact_text_overrides)),
        "source_free": True,
        "status": expected_status,
        "supports_approval_request": True,
    }


def _payload_for_spec(
    spec: Mapping[str, object],
    artifact_text_overrides: Mapping[str, str] | None,
) -> Mapping[str, object]:
    text = _text_for_spec(spec, artifact_text_overrides)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request artifact JSON drift"
        ) from exc
    if not isinstance(payload, Mapping):
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request artifact payload drift"
        )
    return payload


def _text_for_spec(
    spec: Mapping[str, object],
    artifact_text_overrides: Mapping[str, str] | None,
) -> str:
    artifact_id = str(spec["artifact_id"])
    if artifact_text_overrides and artifact_id in artifact_text_overrides:
        text = artifact_text_overrides[artifact_id]
        _assert_text_is_source_free(text)
        return text
    path = spec["relative_path"]
    if not isinstance(path, Path):
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request artifact path spec drift"
        )
    return _read_artifact_text(path)


def _assert_request_payloads(payloads: Mapping[str, Mapping[str, object]]) -> None:
    readiness = payloads["real_triton_first_slice_admission_readiness_gate"]
    review = payloads["source_ingestion_maintainer_security_review_packet"]
    approval = payloads["source_ingestion_maintainer_approval_artifact"]
    admission = payloads["source_ingestion_admission_gate"]

    _assert_false(readiness, "gate_passed")
    _assert_false(readiness, "admission_ready")
    _assert_false(readiness, "admitted")
    _assert_false(readiness, "surface_opened")
    _assert_list_exact(
        readiness.get("remaining_external_evidence"),
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EXTERNAL_EVIDENCE,
        "readiness remaining external evidence",
    )
    if review.get("approval_status") != "not_approved":
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request review approval status drift"
        )
    _assert_list_exact(
        review.get("remaining_external_evidence"),
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EXTERNAL_EVIDENCE,
        "review remaining external evidence",
    )
    _assert_false(approval, "approval_artifact_present")
    _assert_false(approval, "external_approval_artifact_present")
    _assert_false(approval, "admitted")
    _assert_false(approval, "source_ingestion_admission_ready")
    _assert_false(admission, "approval_artifact_present")
    _assert_false(admission, "admitted")
    _assert_false(admission, "source_ingestion_admission_ready")
    _assert_false(admission, "direct_source_ingestion")
    _assert_false(admission, "source_to_compute_graph")
    _assert_false(admission, "source_to_hac_ir")
    _assert_false(admission, "source_to_runtime_plan")


def _assert_review_packets(value: object) -> None:
    if not isinstance(value, list):
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request review packets must be list"
        )
    if len(value) != len(REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_IDS):
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request review packet count drift"
        )
    for item, expected_id, spec in zip(
        value,
        REAL_TRITON_FIRST_SLICE_MAINTAINER_APPROVAL_REQUEST_EVIDENCE_IDS,
        _EVIDENCE_SPECS,
        strict=True,
    ):
        if not isinstance(item, Mapping) or set(item) != _EVIDENCE_KEYS:
            raise RealTritonFirstSliceMaintainerApprovalRequestError(
                "first-slice maintainer approval request review packet item drift"
            )
        if item.get("artifact_id") != expected_id:
            raise RealTritonFirstSliceMaintainerApprovalRequestError(
                "first-slice maintainer approval request evidence order drift"
            )
        if item.get("contract") != spec["expected_contract"]:
            raise RealTritonFirstSliceMaintainerApprovalRequestError(
                "first-slice maintainer approval request evidence contract drift"
            )
        if item.get("status") != spec["expected_status"]:
            raise RealTritonFirstSliceMaintainerApprovalRequestError(
                "first-slice maintainer approval request evidence status drift"
            )
        if item.get("source_free") is not True:
            raise RealTritonFirstSliceMaintainerApprovalRequestError(
                "first-slice maintainer approval request source_free drift"
            )
        if item.get("supports_approval_request") is not True:
            raise RealTritonFirstSliceMaintainerApprovalRequestError(
                "first-slice maintainer approval request support flag drift"
            )
        _assert_digest(item.get("digest"), "review packet digest")


def _read_artifact_text(relative_path: Path) -> str:
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request artifact path invalid"
        )
    try:
        text = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request artifact read failed"
        ) from exc
    _assert_text_is_source_free(text)
    return text


def _assert_string_sequence(value: object, expected: tuple[str, ...], label: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            f"first-slice maintainer approval request {label} drift"
        )


def _assert_list_exact(value: object, expected: tuple[str, ...], label: str) -> None:
    if not isinstance(value, list) or tuple(value) != expected:
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            f"first-slice maintainer approval request {label} drift"
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            "first-slice maintainer approval request expected list"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _TOKEN_RE.fullmatch(item):
            raise RealTritonFirstSliceMaintainerApprovalRequestError(
                "first-slice maintainer approval request token invalid"
            )
        result.append(item)
    return result


def _assert_false(payload: Mapping[str, object], key: str) -> None:
    if payload.get(key) is not False:
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            f"first-slice maintainer approval request {key} drift"
        )


def _assert_digest(value: object, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise RealTritonFirstSliceMaintainerApprovalRequestError(
            f"first-slice maintainer approval request {label} invalid"
        )


def _digest(text: str) -> str:
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise RealTritonFirstSliceMaintainerApprovalRequestError(
                f"first-slice maintainer approval request forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
