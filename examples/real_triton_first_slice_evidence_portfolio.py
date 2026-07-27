"""Emit the Real Triton first-slice evidence portfolio report."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

from examples.first_real_triton_kernel_path import (
    FIRST_REAL_TRITON_KERNEL_PATH_CONTRACT,
    FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_ID,
    FIRST_REAL_TRITON_KERNEL_PATH_STATUS,
    assert_first_real_triton_kernel_path_report_contract,
)
from examples.first_real_triton_kernel_path import (
    build_report as build_first_real_triton_kernel_path_report,
)
from examples.real_triton_first_slice_plan import (
    REAL_TRITON_FIRST_SLICE_PLAN_CONTRACT,
    REAL_TRITON_FIRST_SLICE_PLAN_ID,
    REAL_TRITON_FIRST_SLICE_PLAN_STATUS,
    assert_real_triton_first_slice_plan_report_contract,
)
from examples.real_triton_first_slice_plan import (
    build_report as build_real_triton_first_slice_plan_report,
)
from examples.source_ingestion_admission_gate import (
    SOURCE_INGESTION_ADMISSION_GATE_CONTRACT,
    assert_source_ingestion_admission_gate_report_contract,
)
from examples.source_ingestion_admission_gate import (
    build_report as build_source_ingestion_admission_gate_report,
)
from examples.source_ingestion_maintainer_approval_artifact import (
    assert_source_ingestion_maintainer_approval_artifact_report_contract,
)
from examples.source_ingestion_maintainer_approval_artifact import (
    build_report as build_source_ingestion_maintainer_approval_report,
)
from examples.source_ingestion_maintainer_security_review_packet import (
    SOURCE_INGESTION_MAINTAINER_REVIEW_EVIDENCE_ID,
    assert_source_ingestion_maintainer_security_review_packet_contract,
)
from examples.source_ingestion_maintainer_security_review_packet import (
    build_report as build_source_ingestion_maintainer_review_report,
)
from examples.source_ingestion_preclaim_acyclicity_gate import (
    SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_CONTRACT,
    SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_ID,
    SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_STATUS,
    assert_source_ingestion_preclaim_acyclicity_gate_report_contract,
)
from examples.source_ingestion_preclaim_acyclicity_gate import (
    build_report as build_source_ingestion_preclaim_acyclicity_gate_report,
)
from tuc.frontend.source_ingestion_admission_gate import (
    SOURCE_INGESTION_ADMISSION_GATE_ID,
    SOURCE_INGESTION_ADMISSION_GATE_STATUS,
)
from tuc.frontend.source_ingestion_maintainer_approval import (
    SOURCE_INGESTION_MAINTAINER_APPROVAL_CONTRACT,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_ID,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_STATUS,
)
from tuc.frontend.source_ingestion_maintainer_review import (
    SOURCE_INGESTION_MAINTAINER_REVIEW_CONTRACT,
    SOURCE_INGESTION_MAINTAINER_REVIEW_STATUS,
)

REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_REPORT_SCHEMA_VERSION = (
    "tuc.real_triton_first_slice_evidence_portfolio_report.v0"
)
REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_CONTRACT = (
    "real_triton_first_slice_evidence_portfolio.research_boundary.v0"
)
REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_ID = (
    "real_triton_first_slice_evidence_portfolio"
)
REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_STATUS = "PASS"
REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_SCOPE = (
    "bounded_research_proof_not_source_ingestion_admission"
)
REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_TARGET_SURFACE = (
    "direct_source_ingestion"
)
REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_TARGET_SLICE = (
    "bounded_source_buffer_to_source_intent_plain_data"
)
REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_EVIDENCE_POLICY = (
    "digest_only_source_free"
)
REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_PROVEN_CLAIMS = (
    "first_real_mvp_pipeline_kernel_path_passed",
    "source_intent_reintake_to_runtime_evidence_bound",
    "backend_equivalence_metadata_bound",
    "first_slice_prerequisite_evidence_bound",
    "source_ingestion_admission_fail_closed",
    "project_scope_remains_research_only",
)
REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_BLOCKED_CLAIMS = (
    "arbitrary_triton_source_ingestion",
    "production_source_parser",
    "source_to_compute_graph_admission",
    "native_backend_execution",
    "native_performance_parity",
    "cuda_replacement",
    "runtime_handle_residency",
)
REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_SAFETY_INVARIANTS = (
    "source_ingestion_admitted_false",
    "direct_source_ingestion_false",
    "external_approval_present_false",
    "production_compiler_claim_false",
    "native_performance_claim_false",
    "vendor_replacement_claim_false",
    "triton_jit_execution_false",
    "device_access_false",
    "generated_artifact_execution_false",
    "digest_only_source_free",
)

_BINDING_SPECS = (
    (
        REAL_TRITON_FIRST_SLICE_PLAN_ID,
        "json_report",
        REAL_TRITON_FIRST_SLICE_PLAN_CONTRACT,
        REAL_TRITON_FIRST_SLICE_PLAN_STATUS,
        "plan_id",
        "plan_contract",
        "plan_status",
    ),
    (
        SOURCE_INGESTION_MAINTAINER_REVIEW_EVIDENCE_ID,
        "json_report",
        SOURCE_INGESTION_MAINTAINER_REVIEW_CONTRACT,
        SOURCE_INGESTION_MAINTAINER_REVIEW_STATUS,
        "evidence_id",
        "contract",
        "status",
    ),
    (
        SOURCE_INGESTION_MAINTAINER_APPROVAL_ID,
        "json_report",
        SOURCE_INGESTION_MAINTAINER_APPROVAL_CONTRACT,
        SOURCE_INGESTION_MAINTAINER_APPROVAL_STATUS,
        "evidence_id",
        "contract",
        "status",
    ),
    (
        SOURCE_INGESTION_ADMISSION_GATE_ID,
        "json_report",
        SOURCE_INGESTION_ADMISSION_GATE_CONTRACT,
        SOURCE_INGESTION_ADMISSION_GATE_STATUS,
        "gate_id",
        "gate_contract",
        "gate_status",
    ),
    (
        SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_ID,
        "json_report",
        SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_CONTRACT,
        SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_STATUS,
        "gate_id",
        "gate_contract",
        "gate_status",
    ),
    (
        FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_ID,
        "json_report",
        FIRST_REAL_TRITON_KERNEL_PATH_CONTRACT,
        FIRST_REAL_TRITON_KERNEL_PATH_STATUS,
        "proof_id",
        "path_contract",
        "status",
    ),
)

REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_BINDING_IDS = tuple(
    spec[0] for spec in _BINDING_SPECS
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "admission_status",
        "admitted",
        "blocked_claims",
        "device_access",
        "direct_source_ingestion",
        "evidence",
        "evidence_count",
        "evidence_policy",
        "external_approval_present",
        "first_real_path_status",
        "generated_artifact_execution",
        "issues",
        "native_performance_claim",
        "portfolio_contract",
        "portfolio_id",
        "portfolio_scope",
        "portfolio_status",
        "production_compiler_claim",
        "proven_claims",
        "research_scope_claim",
        "runtime_handle_residency_claim",
        "safety_invariants",
        "schema_version",
        "source_ingestion_admission_ready",
        "surface_opened",
        "target_slice",
        "target_surface",
        "triton_jit_execution",
        "vendor_replacement_claim",
    }
)
_BINDING_KEYS = frozenset(
    {
        "artifact_id",
        "artifact_kind",
        "contract",
        "digest",
        "source_free",
        "status",
        "supports_portfolio",
    }
)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import os",
    "import triton",
    "tl.dot",
    "tl.store",
    '"backend_artifact":',
    '"command_line":',
    '"device_id":',
    '"file_path":',
    '"generated_code":',
    '"host_path":',
    '"module_source":',
    '"plugin_entrypoint":',
    '"python_source":',
    '"raw_source":',
    '"raw_source_text":',
    '"raw_tensor_value":',
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_text":',
)


class RealTritonFirstSliceEvidencePortfolioError(AssertionError):
    """Raised when the Real Triton first-slice evidence portfolio drifts."""


def build_real_triton_first_slice_evidence_portfolio_report() -> dict[str, object]:
    """Return the digest-bound portfolio for the first Real Triton slice."""

    texts = _build_texts()
    payloads = _build_payloads(texts)
    _assert_supporting_payloads(payloads)
    evidence = [
        _binding_from_payload(payloads[evidence_id], texts[evidence_id], spec)
        for spec in _BINDING_SPECS
        for evidence_id in (spec[0],)
    ]
    report: dict[str, object] = {
        "admission_status": "blocked",
        "admitted": False,
        "blocked_claims": list(
            REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_BLOCKED_CLAIMS
        ),
        "device_access": False,
        "direct_source_ingestion": False,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "evidence_policy": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_EVIDENCE_POLICY,
        "external_approval_present": False,
        "first_real_path_status": FIRST_REAL_TRITON_KERNEL_PATH_STATUS,
        "generated_artifact_execution": False,
        "issues": [],
        "native_performance_claim": False,
        "portfolio_contract": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_CONTRACT,
        "portfolio_id": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_ID,
        "portfolio_scope": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_SCOPE,
        "portfolio_status": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_STATUS,
        "production_compiler_claim": False,
        "proven_claims": list(
            REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_PROVEN_CLAIMS
        ),
        "research_scope_claim": True,
        "runtime_handle_residency_claim": False,
        "safety_invariants": list(
            REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_SAFETY_INVARIANTS
        ),
        "schema_version": (
            REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_REPORT_SCHEMA_VERSION
        ),
        "source_ingestion_admission_ready": False,
        "surface_opened": False,
        "target_slice": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_TARGET_SLICE,
        "target_surface": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_TARGET_SURFACE,
        "triton_jit_execution": False,
        "vendor_replacement_claim": False,
    }
    assert_real_triton_first_slice_evidence_portfolio_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the Real Triton first-slice portfolio."""

    return json.dumps(
        build_real_triton_first_slice_evidence_portfolio_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_real_triton_first_slice_evidence_portfolio_report_contract(
    report: object,
) -> None:
    """Fail closed unless the first-slice evidence portfolio matches v0."""

    if not isinstance(report, Mapping):
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio report must be object"
        )
    if set(report) != _TOP_LEVEL_KEYS:
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio top-level keys drift"
        )
    expected = {
        "admission_status": "blocked",
        "admitted": False,
        "device_access": False,
        "direct_source_ingestion": False,
        "evidence_count": len(_BINDING_SPECS),
        "evidence_policy": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_EVIDENCE_POLICY,
        "external_approval_present": False,
        "first_real_path_status": FIRST_REAL_TRITON_KERNEL_PATH_STATUS,
        "generated_artifact_execution": False,
        "native_performance_claim": False,
        "portfolio_contract": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_CONTRACT,
        "portfolio_id": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_ID,
        "portfolio_scope": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_SCOPE,
        "portfolio_status": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_STATUS,
        "production_compiler_claim": False,
        "research_scope_claim": True,
        "runtime_handle_residency_claim": False,
        "schema_version": (
            REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_REPORT_SCHEMA_VERSION
        ),
        "source_ingestion_admission_ready": False,
        "surface_opened": False,
        "target_slice": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_TARGET_SLICE,
        "target_surface": REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_TARGET_SURFACE,
        "triton_jit_execution": False,
        "vendor_replacement_claim": False,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise RealTritonFirstSliceEvidencePortfolioError(
                f"first-slice portfolio {key} drift"
            )
    _assert_string_sequence(
        report.get("proven_claims"),
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_PROVEN_CLAIMS,
        "proven_claims",
    )
    _assert_string_sequence(
        report.get("blocked_claims"),
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_BLOCKED_CLAIMS,
        "blocked_claims",
    )
    _assert_string_sequence(
        report.get("safety_invariants"),
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_SAFETY_INVARIANTS,
        "safety_invariants",
    )
    _assert_evidence(report.get("evidence"))
    if report.get("issues") != []:
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio issues must be empty"
        )
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_texts() -> dict[str, str]:
    return {
        REAL_TRITON_FIRST_SLICE_PLAN_ID: build_real_triton_first_slice_plan_report(),
        SOURCE_INGESTION_MAINTAINER_REVIEW_EVIDENCE_ID: (
            build_source_ingestion_maintainer_review_report()
        ),
        SOURCE_INGESTION_MAINTAINER_APPROVAL_ID: (
            build_source_ingestion_maintainer_approval_report()
        ),
        SOURCE_INGESTION_ADMISSION_GATE_ID: (
            build_source_ingestion_admission_gate_report()
        ),
        SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_ID: (
            build_source_ingestion_preclaim_acyclicity_gate_report()
        ),
        FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_ID: (
            build_first_real_triton_kernel_path_report()
        ),
    }


def _build_payloads(texts: Mapping[str, str]) -> dict[str, Mapping[str, object]]:
    return {
        evidence_id: _json_payload(text, evidence_id)
        for evidence_id, text in texts.items()
    }


def _assert_supporting_payloads(
    payloads: Mapping[str, Mapping[str, object]],
) -> None:
    plan = payloads[REAL_TRITON_FIRST_SLICE_PLAN_ID]
    assert_real_triton_first_slice_plan_report_contract(plan)
    if plan.get("admitted") is not False:
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio plan admitted drift"
        )

    review = payloads[SOURCE_INGESTION_MAINTAINER_REVIEW_EVIDENCE_ID]
    assert_source_ingestion_maintainer_security_review_packet_contract(review)
    if review.get("approval_status") != "not_approved":
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio review approval drift"
        )
    _assert_closed_ingestion_surface(review, "review")

    approval = payloads[SOURCE_INGESTION_MAINTAINER_APPROVAL_ID]
    assert_source_ingestion_maintainer_approval_artifact_report_contract(approval)
    if approval.get("approval_artifact_present") is not False:
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio approval artifact drift"
        )
    if approval.get("external_approval_artifact_present") is not False:
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio external approval drift"
        )
    if approval.get("admitted") is not False:
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio approval admitted drift"
        )
    _assert_closed_ingestion_surface(approval, "approval")

    admission = payloads[SOURCE_INGESTION_ADMISSION_GATE_ID]
    assert_source_ingestion_admission_gate_report_contract(admission)
    if admission.get("admission_status") != "blocked":
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio admission status drift"
        )
    if admission.get("admitted") is not False:
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio admission admitted drift"
        )
    _assert_closed_ingestion_surface(admission, "admission")

    preclaim = payloads[SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_ID]
    assert_source_ingestion_preclaim_acyclicity_gate_report_contract(preclaim)
    if preclaim.get("cycle_count") != 0 or preclaim.get("source_free") is not True:
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio preclaim acyclicity drift"
        )

    first_path = payloads[FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_ID]
    assert_first_real_triton_kernel_path_report_contract(first_path)
    if first_path.get("status") != FIRST_REAL_TRITON_KERNEL_PATH_STATUS:
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio first path status drift"
        )



def _assert_closed_ingestion_surface(
    payload: Mapping[str, object],
    label: str,
) -> None:
    expected_false_fields = (
        "direct_source_ingestion",
        "source_ingestion_admission_ready",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_runtime_plan",
    )
    for field_name in expected_false_fields:
        if payload.get(field_name) is not False:
            raise RealTritonFirstSliceEvidencePortfolioError(
                f"first-slice portfolio {label} {field_name} drift"
            )


def _binding_from_payload(
    payload: Mapping[str, object],
    text: str,
    spec: tuple[str, str, str, str, str, str, str],
) -> dict[str, object]:
    artifact_id, artifact_kind, contract, status, id_key, contract_key, status_key = spec
    observed = {
        "artifact_id": payload.get(id_key),
        "contract": payload.get(contract_key),
        "status": payload.get(status_key),
    }
    expected = {
        "artifact_id": artifact_id,
        "contract": contract,
        "status": status,
    }
    for key, expected_value in expected.items():
        if observed[key] != expected_value:
            raise RealTritonFirstSliceEvidencePortfolioError(
                f"first-slice portfolio binding {key} drift"
            )
    return {
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "contract": contract,
        "digest": _digest(text),
        "source_free": True,
        "status": status,
        "supports_portfolio": True,
    }


def _assert_evidence(value: object) -> None:
    if not isinstance(value, list):
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio evidence must be list"
        )
    if len(value) != len(_BINDING_SPECS):
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio evidence count drift"
        )
    observed_ids = []
    observed_statuses = []
    for item, expected in zip(value, _BINDING_SPECS, strict=True):
        observed_ids.append(_assert_evidence_item(item, expected))
        if isinstance(item, Mapping):
            observed_statuses.append(item.get("status"))
    if tuple(observed_ids) != REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_BINDING_IDS:
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio evidence ID drift"
        )
    if tuple(observed_statuses) != tuple(spec[3] for spec in _BINDING_SPECS):
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio evidence status drift"
        )


def _assert_evidence_item(
    item: object,
    expected: tuple[str, str, str, str, str, str, str],
) -> str:
    if not isinstance(item, Mapping):
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio evidence item invalid"
        )
    if set(item) != _BINDING_KEYS:
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio evidence keys drift"
        )
    artifact_id, artifact_kind, contract, status, *_ = expected
    expected_values = {
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "contract": contract,
        "source_free": True,
        "status": status,
        "supports_portfolio": True,
    }
    for key, expected_value in expected_values.items():
        if item.get(key) != expected_value:
            raise RealTritonFirstSliceEvidencePortfolioError(
                f"first-slice portfolio evidence {key} drift"
            )
    digest = item.get("digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio digest drift"
        )
    return artifact_id


def _json_payload(text: str, evidence_id: str) -> Mapping[str, object]:
    _assert_text_is_source_free(text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RealTritonFirstSliceEvidencePortfolioError(
            f"first-slice portfolio {evidence_id} JSON drift"
        ) from exc
    if not isinstance(payload, Mapping):
        raise RealTritonFirstSliceEvidencePortfolioError(
            f"first-slice portfolio {evidence_id} payload drift"
        )
    return payload


def _assert_string_sequence(
    value: object,
    expected: tuple[str, ...],
    field_name: str,
) -> None:
    if tuple(_string_list(value)) != expected:
        raise RealTritonFirstSliceEvidencePortfolioError(
            f"first-slice portfolio {field_name} drift"
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise RealTritonFirstSliceEvidencePortfolioError(
            "first-slice portfolio expected string list"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _TOKEN_RE.fullmatch(item):
            raise RealTritonFirstSliceEvidencePortfolioError(
                "first-slice portfolio string list item invalid"
            )
        result.append(item)
    return result


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise RealTritonFirstSliceEvidencePortfolioError(
                f"first-slice portfolio contains forbidden fragment: {fragment}"
            )


def _digest(text: str) -> str:
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
