"""Emit the Real Triton first-slice admission readiness gate report."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_SCHEMA_VERSION = (
    "tuc.real_triton_first_slice_admission_readiness_gate_report.v0"
)
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_CONTRACT = (
    "real_triton_first_slice_admission_readiness_gate.data_only.v0"
)
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_ID = (
    "real_triton_first_slice_admission_readiness_gate"
)
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_STATUS = (
    "blocked_missing_maintainer_security_review_approval"
)
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_DECISION = "deny_until_external_approval"
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_TARGET_SURFACE = "direct_source_ingestion"
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_TARGET_SLICE = (
    "bounded_source_buffer_to_source_intent_plain_data"
)
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_POLICY = (
    "digest_only_fixed_artifact_scan"
)
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REMAINING_EXTERNAL_EVIDENCE = (
    "maintainer_security_review_approval",
)
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKING_REASONS = (
    "maintainer_security_review_approval_missing",
)
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_ALREADY_SATISFIED = (
    "first_slice_plan_bound",
    "maintainer_review_packet_ready",
    "maintainer_approval_absence_bound",
    "source_ingestion_admission_gate_fail_closed",
    "first_real_triton_kernel_path_passed",
    "first_slice_evidence_portfolio_passed",
    "objective_alpha_catalog_acyclicity_passed",
)
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKED_CLAIMS = (
    "arbitrary_triton_source_ingestion",
    "production_parser",
    "source_to_compute_graph_admission",
    "native_backend_execution",
    "native_performance_parity",
    "vendor_replacement",
)
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKED_EXECUTION_SURFACES = (
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
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REQUIRED_INVARIANTS = (
    "first_slice_plan_bound",
    "maintainer_review_packet_ready",
    "external_approval_artifact_absent",
    "source_ingestion_admission_gate_fail_closed",
    "first_real_kernel_path_passed",
    "first_slice_evidence_portfolio_passed",
    "catalog_acyclicity_passed",
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
        "artifact_id": "real_triton_first_admissible_slice_plan",
        "relative_path": Path("tests/golden/frontend/real_triton_first_slice_plan_report.json"),
        "contract_key": "plan_contract",
        "status_key": "plan_status",
        "expected_contract": "real_triton_first_slice_plan.data_only.v0",
        "expected_status": "blocked_until_admitting_source_ingestion_evidence",
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
    {
        "artifact_id": "first_real_triton_kernel_path",
        "relative_path": Path("tests/golden/frontend/first_real_triton_kernel_path.json"),
        "contract_key": "path_contract",
        "status_key": "status",
        "expected_contract": "first_real_triton_kernel_path.digest_bound.v0",
        "expected_status": "PASS",
    },
    {
        "artifact_id": "real_triton_first_slice_evidence_portfolio",
        "relative_path": Path(
            "tests/golden/frontend/real_triton_first_slice_evidence_portfolio_report.json"
        ),
        "contract_key": "portfolio_contract",
        "status_key": "portfolio_status",
        "expected_contract": "real_triton_first_slice_evidence_portfolio.research_boundary.v0",
        "expected_status": "PASS",
    },
    {
        "artifact_id": "objective_alpha_catalog_acyclicity_gate",
        "relative_path": Path("tests/golden/proofs/objective_alpha_catalog_acyclicity_gate.json"),
        "contract_key": "gate_contract",
        "status_key": "gate_status",
        "expected_contract": "objective_alpha.catalog_acyclicity_gate.data_only.v0",
        "expected_status": "PASS",
    },
)
REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_IDS = tuple(
    str(spec["artifact_id"]) for spec in _EVIDENCE_SPECS
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "admission_decision",
        "admission_ready",
        "admitted",
        "already_satisfied",
        "already_satisfied_count",
        "artifact_status",
        "blocked_claims",
        "blocked_execution_surfaces",
        "blocking_reasons",
        "checked_evidence",
        "checked_evidence_count",
        "evidence_policy",
        "gate_contract",
        "gate_id",
        "gate_passed",
        "gate_status",
        "issues",
        "remaining_external_evidence",
        "remaining_external_evidence_count",
        "required_invariants",
        "schema_version",
        "source_free",
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
        "supports_readiness_gate",
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


class RealTritonFirstSliceAdmissionReadinessGateError(AssertionError):
    """Raised when first-slice admission readiness evidence drifts."""


def build_real_triton_first_slice_admission_readiness_gate_report(
    *,
    artifact_text_overrides: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Return a source-free blocked readiness gate report for the first slice."""

    evidence = tuple(
        _build_evidence_item(spec, artifact_text_overrides) for spec in _EVIDENCE_SPECS
    )
    payloads = {
        str(spec["artifact_id"]): _payload_for_spec(spec, artifact_text_overrides)
        for spec in _EVIDENCE_SPECS
    }
    _assert_first_slice_readiness_payloads(payloads)

    report: dict[str, object] = {
        "admission_decision": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_DECISION,
        "admission_ready": False,
        "admitted": False,
        "already_satisfied": list(REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_ALREADY_SATISFIED),
        "already_satisfied_count": len(
            REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_ALREADY_SATISFIED
        ),
        "artifact_status": "review_gate",
        "blocked_claims": list(REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKED_CLAIMS),
        "blocked_execution_surfaces": list(
            REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKED_EXECUTION_SURFACES
        ),
        "blocking_reasons": list(REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKING_REASONS),
        "checked_evidence": [dict(item) for item in evidence],
        "checked_evidence_count": len(REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_IDS),
        "evidence_policy": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_POLICY,
        "gate_contract": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_CONTRACT,
        "gate_id": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_ID,
        "gate_passed": False,
        "gate_status": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_STATUS,
        "issues": [],
        "remaining_external_evidence": list(
            REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REMAINING_EXTERNAL_EVIDENCE
        ),
        "remaining_external_evidence_count": len(
            REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REMAINING_EXTERNAL_EVIDENCE
        ),
        "required_invariants": list(
            REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REQUIRED_INVARIANTS
        ),
        "schema_version": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_SCHEMA_VERSION,
        "source_free": True,
        "surface_opened": False,
        "target_slice": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_TARGET_SLICE,
        "target_surface": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_TARGET_SURFACE,
    }
    assert_real_triton_first_slice_admission_readiness_gate_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the first-slice readiness gate."""

    return json.dumps(
        build_real_triton_first_slice_admission_readiness_gate_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_real_triton_first_slice_admission_readiness_gate_report_contract(
    report: object,
) -> None:
    """Fail closed unless the report matches the current v0 readiness contract."""

    if not isinstance(report, Mapping):
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness report must be object"
        )
    if set(report) != _TOP_LEVEL_KEYS:
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness top-level keys drift"
        )
    expected = {
        "admission_decision": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_DECISION,
        "admission_ready": False,
        "admitted": False,
        "already_satisfied_count": len(
            REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_ALREADY_SATISFIED
        ),
        "artifact_status": "review_gate",
        "checked_evidence_count": len(
            REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_IDS
        ),
        "evidence_policy": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_POLICY,
        "gate_contract": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_CONTRACT,
        "gate_id": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_ID,
        "gate_passed": False,
        "gate_status": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_STATUS,
        "remaining_external_evidence_count": len(
            REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REMAINING_EXTERNAL_EVIDENCE
        ),
        "schema_version": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_SCHEMA_VERSION,
        "source_free": True,
        "surface_opened": False,
        "target_slice": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_TARGET_SLICE,
        "target_surface": REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_TARGET_SURFACE,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise RealTritonFirstSliceAdmissionReadinessGateError(
                f"first-slice admission readiness {key} drift"
            )
    _assert_string_sequence(
        report.get("already_satisfied"),
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_ALREADY_SATISFIED,
        "already_satisfied",
    )
    _assert_string_sequence(
        report.get("blocked_claims"),
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKED_CLAIMS,
        "blocked_claims",
    )
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("blocking_reasons"),
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKING_REASONS,
        "blocking_reasons",
    )
    _assert_string_sequence(
        report.get("remaining_external_evidence"),
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REMAINING_EXTERNAL_EVIDENCE,
        "remaining_external_evidence",
    )
    _assert_string_sequence(
        report.get("required_invariants"),
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REQUIRED_INVARIANTS,
        "required_invariants",
    )
    if report.get("issues") != []:
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness issues must be empty"
        )
    _assert_evidence(report.get("checked_evidence"))
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_evidence_item(
    spec: Mapping[str, object],
    artifact_text_overrides: Mapping[str, str] | None,
) -> Mapping[str, object]:
    payload = _payload_for_spec(spec, artifact_text_overrides)
    contract_key = str(spec["contract_key"])
    status_key = str(spec["status_key"])
    expected_contract = str(spec["expected_contract"])
    expected_status = str(spec["expected_status"])
    contract = payload.get(contract_key)
    status = payload.get(status_key)
    if contract != expected_contract or status != expected_status:
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness evidence status drift"
        )
    return {
        "artifact_id": str(spec["artifact_id"]),
        "contract": expected_contract,
        "digest": _digest(_text_for_spec(spec, artifact_text_overrides)),
        "source_free": True,
        "status": expected_status,
        "supports_readiness_gate": True,
    }


def _payload_for_spec(
    spec: Mapping[str, object],
    artifact_text_overrides: Mapping[str, str] | None,
) -> Mapping[str, object]:
    text = _text_for_spec(spec, artifact_text_overrides)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness artifact JSON drift"
        ) from exc
    if not isinstance(payload, Mapping):
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness artifact payload drift"
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
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness artifact path spec drift"
        )
    return _read_artifact_text(path)


def _assert_first_slice_readiness_payloads(payloads: Mapping[str, Mapping[str, object]]) -> None:
    plan = payloads["real_triton_first_admissible_slice_plan"]
    review = payloads["source_ingestion_maintainer_security_review_packet"]
    approval = payloads["source_ingestion_maintainer_approval_artifact"]
    admission = payloads["source_ingestion_admission_gate"]
    kernel = payloads["first_real_triton_kernel_path"]
    portfolio = payloads["real_triton_first_slice_evidence_portfolio"]
    catalog = payloads["objective_alpha_catalog_acyclicity_gate"]

    _assert_false(plan, "admitted")
    _assert_false(plan, "source_ingestion_admission_ready")
    _assert_list_exact(
        plan.get("missing_admission_evidence"),
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REMAINING_EXTERNAL_EVIDENCE,
        "plan missing admission evidence",
    )
    if review.get("approval_status") != "not_approved":
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness review approval status drift"
        )
    _assert_list_exact(
        review.get("remaining_external_evidence"),
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REMAINING_EXTERNAL_EVIDENCE,
        "review remaining external evidence",
    )
    _assert_false(approval, "approval_artifact_present")
    _assert_false(approval, "source_ingestion_admission_ready")
    _assert_false(admission, "admitted")
    _assert_false(admission, "source_ingestion_admission_ready")
    _assert_false(admission, "direct_source_ingestion")
    _assert_false(admission, "source_to_compute_graph")
    _assert_false(admission, "source_to_hac_ir")
    _assert_false(admission, "source_to_runtime_plan")
    if (
        kernel.get("status") != "PASS"
        or kernel.get("default_parser_status") != "default_parser_blocked"
    ):
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness kernel path status drift"
        )
    _assert_false(portfolio, "admitted")
    _assert_false(portfolio, "direct_source_ingestion")
    _assert_false(portfolio, "source_ingestion_admission_ready")
    _assert_false(portfolio, "surface_opened")
    if catalog.get("gate_status") != "PASS" or catalog.get("cycle_count") != 0:
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness catalog acyclicity drift"
        )


def _assert_evidence(value: object) -> None:
    if not isinstance(value, list):
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness evidence must be list"
        )
    if len(value) != len(REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_IDS):
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness evidence count drift"
        )
    for item, expected_id, spec in zip(
        value,
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_IDS,
        _EVIDENCE_SPECS,
        strict=True,
    ):
        if not isinstance(item, Mapping) or set(item) != _EVIDENCE_KEYS:
            raise RealTritonFirstSliceAdmissionReadinessGateError(
                "first-slice admission readiness evidence item drift"
            )
        if item.get("artifact_id") != expected_id:
            raise RealTritonFirstSliceAdmissionReadinessGateError(
                "first-slice admission readiness evidence id drift"
            )
        if item.get("contract") != spec["expected_contract"]:
            raise RealTritonFirstSliceAdmissionReadinessGateError(
                "first-slice admission readiness evidence contract drift"
            )
        if item.get("status") != spec["expected_status"]:
            raise RealTritonFirstSliceAdmissionReadinessGateError(
                "first-slice admission readiness evidence status drift"
            )
        if item.get("source_free") is not True or item.get("supports_readiness_gate") is not True:
            raise RealTritonFirstSliceAdmissionReadinessGateError(
                "first-slice admission readiness evidence flag drift"
            )
        _assert_digest(item.get("digest"), "evidence digest")


def _read_artifact_text(relative_path: Path) -> str:
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness artifact path invalid"
        )
    try:
        text = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness artifact read failed"
        ) from exc
    _assert_text_is_source_free(text)
    return text


def _assert_string_sequence(value: object, expected: tuple[str, ...], label: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            f"first-slice admission readiness {label} drift"
        )


def _assert_list_exact(value: object, expected: tuple[str, ...], label: str) -> None:
    if not isinstance(value, list) or tuple(value) != expected:
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            f"first-slice admission readiness {label} drift"
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            "first-slice admission readiness expected list"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _TOKEN_RE.fullmatch(item):
            raise RealTritonFirstSliceAdmissionReadinessGateError(
                "first-slice admission readiness token invalid"
            )
        result.append(item)
    return result


def _assert_false(payload: Mapping[str, object], key: str) -> None:
    if payload.get(key) is not False:
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            f"first-slice admission readiness {key} drift"
        )


def _assert_digest(value: object, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise RealTritonFirstSliceAdmissionReadinessGateError(
            f"first-slice admission readiness {label} invalid"
        )


def _digest(text: str) -> str:
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise RealTritonFirstSliceAdmissionReadinessGateError(
                f"first-slice admission readiness forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
