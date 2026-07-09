"""Emit the next Real Triton first-slice plan report."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from hashlib import sha256

from examples.admitting_source_ingestion_rfc import (
    ADMITTING_SOURCE_INGESTION_RFC_REMAINING_EVIDENCE,
)
from examples.admitting_source_ingestion_rfc import (
    build_report as build_admitting_source_ingestion_rfc_report,
)
from examples.bounded_source_buffer_api import (
    build_report as build_bounded_source_buffer_api_report,
)
from examples.parser_fuzz_negative_corpus_for_admitting_slice import (
    build_report as build_parser_fuzz_negative_corpus_report,
)
from examples.real_triton_integration_admission_gate import (
    build_report as build_real_triton_admission_report,
)
from examples.real_triton_surface_gate_completion import (
    build_report as build_surface_gate_completion_report,
)
from examples.source_ingestion_quarantine_gate import (
    build_report as build_source_ingestion_quarantine_report,
)
from examples.source_ingestion_sandbox_implementation import (
    build_report as build_source_ingestion_sandbox_implementation_report,
)
from examples.source_to_intent_research_kernel_ingress_proof_bundle import (
    build_report as build_kernel_ingress_proof_bundle_report,
)
from examples.source_to_intent_research_source_runtime_smoke import (
    build_report as build_source_runtime_smoke_report,
)

REAL_TRITON_FIRST_SLICE_PLAN_REPORT_SCHEMA_VERSION = (
    "tuc.real_triton_first_slice_plan_report.v0"
)
REAL_TRITON_FIRST_SLICE_PLAN_CONTRACT = "real_triton_first_slice_plan.data_only.v0"
REAL_TRITON_FIRST_SLICE_PLAN_ID = "real_triton_first_admissible_slice_plan"
REAL_TRITON_FIRST_SLICE_PLAN_STATUS = "blocked_until_admitting_source_ingestion_evidence"
REAL_TRITON_FIRST_SLICE_PLAN_TARGET_SURFACE = "direct_source_ingestion"
REAL_TRITON_FIRST_SLICE_PLAN_TARGET_SLICE = (
    "bounded_source_buffer_to_source_intent_plain_data"
)
REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_POLICY = "digest_only_source_free"
REAL_TRITON_FIRST_SLICE_PLAN_ADMISSION_STATUS = "blocked"

REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_IDS = (
    "real_triton_integration_admission_gate",
    "real_triton_surface_gate_completion",
    "source_ingestion_quarantine_gate",
    "admitting_source_ingestion_rfc",
    "bounded_source_buffer_api",
    "source_ingestion_sandbox_implementation",
    "parser_fuzz_negative_corpus_for_admitting_slice",
    "source_to_intent_research_source_runtime_smoke",
    "source_to_intent_research_kernel_ingress_proof_bundle",
)
REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_CONTRACT_KEYS = (
    "admission_contract",
    "completion_contract",
    "gate_contract",
    "rfc_contract",
    "api_contract",
    "sandbox_contract",
    "corpus_contract",
    "smoke_contract",
    "bundle_contract",
)
REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_STATUS_KEYS = (
    "admission_status",
    "completion_status",
    "gate_status",
    "proposal_status",
    "api_status",
    "sandbox_status",
    "corpus_status",
    "status",
    "status",
)
REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_EXPECTED_STATUS = (
    "blocked",
    "complete",
    "quarantine_only",
    "accepted_requirements_only",
    "implemented_non_admitting",
    "implemented_non_admitting",
    "complete_non_admitting",
    "PASS",
    "PASS",
)
REAL_TRITON_FIRST_SLICE_PLAN_ALREADY_SATISFIED = (
    "real_triton_admission_gate_bound",
    "surface_gate_completion_bound",
    "source_ingestion_quarantine_bound",
    "admitting_source_ingestion_rfc_bound",
    "bounded_source_buffer_api_bound",
    "source_ingestion_sandbox_implementation_bound",
    "parser_fuzz_negative_corpus_bound",
    "research_source_runtime_smoke_passed",
    "kernel_ingress_proof_bundle_passed",
)
REAL_TRITON_FIRST_SLICE_PLAN_MISSING_ADMISSION_EVIDENCE = (
    "source_free_diagnostics_admission_tests",
    "source_to_intent_plain_data_output_golden_for_admitted_slice",
    "ci_replay_for_admitted_slice",
    "maintainer_security_review_approval",
)
REAL_TRITON_FIRST_SLICE_PLAN_SURFACES_REMAINING_BLOCKED = (
    "frontend_package_import",
    "plugin_discovery",
    "triton_jit_execution",
    "device_access",
    "generated_artifact_execution",
    "native_backend_execution",
)
REAL_TRITON_FIRST_SLICE_PLAN_BLOCKED_CLAIMS = (
    "accepts_arbitrary_triton_source",
    "executes_generated_artifacts",
    "executes_native_backends",
    "imports_external_frontend_packages",
    "runs_triton_jit",
    "uses_real_devices",
)
REAL_TRITON_FIRST_SLICE_PLAN_REQUIRED_INVARIANTS = (
    "admitted_false_until_admitting_rfc_accepted",
    "direct_source_ingestion_false_until_all_admission_evidence",
    "source_to_compute_graph_blocked",
    "source_to_hac_ir_blocked",
    "source_to_runtime_plan_blocked",
    "python_import_blocked",
    "triton_jit_blocked",
    "device_access_blocked",
    "generated_artifact_execution_blocked",
    "digest_only_source_free_evidence",
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "admission_status",
        "admitted",
        "already_satisfied_prerequisites",
        "blocked_claims",
        "evidence",
        "evidence_count",
        "evidence_policy",
        "issues",
        "missing_admission_evidence",
        "missing_admission_evidence_count",
        "plan_contract",
        "plan_id",
        "plan_status",
        "required_invariants",
        "schema_version",
        "source_ingestion_admission_ready",
        "surfaces_remaining_blocked",
        "surfaces_remaining_blocked_count",
        "target_slice",
        "target_surface",
    }
)
_EVIDENCE_KEYS = frozenset(
    {
        "contract",
        "digest",
        "evidence_id",
        "source_free",
        "status",
        "supports_plan",
    }
)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_REPORT_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_FORBIDDEN_TOKENS = frozenset(
    {
        "backend_artifact",
        "command_line",
        "device_id",
        "dynamic_library",
        "file_path",
        "generated_code",
        "host_path",
        "plugin_entrypoint",
        "python_source",
        "raw_source_text",
        "raw_tensor_value",
        "runtime_handle",
        "source_intent_payload",
        "source_text",
        "url",
    }
)
_FORBIDDEN_TEXT_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"backend_artifact":',
    '"command_line":',
    '"device_id":',
    '"file_path":',
    '"generated_code":',
    '"host_path":',
    '"plugin_entrypoint":',
    '"python_source":',
    '"raw_source_text":',
    '"raw_tensor_value":',
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_text":',
)


class RealTritonFirstSlicePlanError(AssertionError):
    """Raised when the Real Triton first-slice plan is not valid."""


@lru_cache(maxsize=1)
def build_real_triton_first_slice_plan_report() -> dict[str, object]:
    """Build the data-only first-slice plan report."""

    payloads = _build_payloads()
    _assert_supporting_payloads(payloads)
    evidence = [
        _evidence_from_payload(evidence_id, payloads[evidence_id], contract_key, status_key)
        for evidence_id, contract_key, status_key in zip(
            REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_IDS,
            REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_CONTRACT_KEYS,
            REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_STATUS_KEYS,
            strict=True,
        )
    ]
    report: dict[str, object] = {
        "admission_status": REAL_TRITON_FIRST_SLICE_PLAN_ADMISSION_STATUS,
        "admitted": False,
        "already_satisfied_prerequisites": list(
            REAL_TRITON_FIRST_SLICE_PLAN_ALREADY_SATISFIED
        ),
        "blocked_claims": list(REAL_TRITON_FIRST_SLICE_PLAN_BLOCKED_CLAIMS),
        "evidence": evidence,
        "evidence_count": len(evidence),
        "evidence_policy": REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_POLICY,
        "issues": [],
        "missing_admission_evidence": list(
            REAL_TRITON_FIRST_SLICE_PLAN_MISSING_ADMISSION_EVIDENCE
        ),
        "missing_admission_evidence_count": len(
            REAL_TRITON_FIRST_SLICE_PLAN_MISSING_ADMISSION_EVIDENCE
        ),
        "plan_contract": REAL_TRITON_FIRST_SLICE_PLAN_CONTRACT,
        "plan_id": REAL_TRITON_FIRST_SLICE_PLAN_ID,
        "plan_status": REAL_TRITON_FIRST_SLICE_PLAN_STATUS,
        "required_invariants": list(REAL_TRITON_FIRST_SLICE_PLAN_REQUIRED_INVARIANTS),
        "schema_version": REAL_TRITON_FIRST_SLICE_PLAN_REPORT_SCHEMA_VERSION,
        "source_ingestion_admission_ready": False,
        "surfaces_remaining_blocked": list(
            REAL_TRITON_FIRST_SLICE_PLAN_SURFACES_REMAINING_BLOCKED
        ),
        "surfaces_remaining_blocked_count": len(
            REAL_TRITON_FIRST_SLICE_PLAN_SURFACES_REMAINING_BLOCKED
        ),
        "target_slice": REAL_TRITON_FIRST_SLICE_PLAN_TARGET_SLICE,
        "target_surface": REAL_TRITON_FIRST_SLICE_PLAN_TARGET_SURFACE,
    }
    assert_real_triton_first_slice_plan_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the first-slice plan."""

    return json.dumps(
        build_real_triton_first_slice_plan_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_real_triton_first_slice_plan_report_contract(report: object) -> None:
    """Fail closed unless the first-slice plan matches v0."""

    if not isinstance(report, Mapping):
        raise RealTritonFirstSlicePlanError("first-slice plan report must be object")
    if set(report) != _TOP_LEVEL_KEYS:
        raise RealTritonFirstSlicePlanError("first-slice plan top-level keys drift")
    expected = {
        "admission_status": REAL_TRITON_FIRST_SLICE_PLAN_ADMISSION_STATUS,
        "admitted": False,
        "evidence_count": len(REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_IDS),
        "evidence_policy": REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_POLICY,
        "missing_admission_evidence_count": len(
            REAL_TRITON_FIRST_SLICE_PLAN_MISSING_ADMISSION_EVIDENCE
        ),
        "plan_contract": REAL_TRITON_FIRST_SLICE_PLAN_CONTRACT,
        "plan_id": REAL_TRITON_FIRST_SLICE_PLAN_ID,
        "plan_status": REAL_TRITON_FIRST_SLICE_PLAN_STATUS,
        "schema_version": REAL_TRITON_FIRST_SLICE_PLAN_REPORT_SCHEMA_VERSION,
        "source_ingestion_admission_ready": False,
        "surfaces_remaining_blocked_count": len(
            REAL_TRITON_FIRST_SLICE_PLAN_SURFACES_REMAINING_BLOCKED
        ),
        "target_slice": REAL_TRITON_FIRST_SLICE_PLAN_TARGET_SLICE,
        "target_surface": REAL_TRITON_FIRST_SLICE_PLAN_TARGET_SURFACE,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise RealTritonFirstSlicePlanError(f"first-slice plan {key} mismatch")
    _assert_string_sequence(
        report.get("already_satisfied_prerequisites"),
        REAL_TRITON_FIRST_SLICE_PLAN_ALREADY_SATISFIED,
        "already_satisfied_prerequisites",
    )
    _assert_string_sequence(
        report.get("missing_admission_evidence"),
        REAL_TRITON_FIRST_SLICE_PLAN_MISSING_ADMISSION_EVIDENCE,
        "missing_admission_evidence",
    )
    _assert_string_sequence(
        report.get("surfaces_remaining_blocked"),
        REAL_TRITON_FIRST_SLICE_PLAN_SURFACES_REMAINING_BLOCKED,
        "surfaces_remaining_blocked",
    )
    _assert_string_sequence(
        report.get("blocked_claims"),
        REAL_TRITON_FIRST_SLICE_PLAN_BLOCKED_CLAIMS,
        "blocked_claims",
    )
    _assert_string_sequence(
        report.get("required_invariants"),
        REAL_TRITON_FIRST_SLICE_PLAN_REQUIRED_INVARIANTS,
        "required_invariants",
    )
    _assert_evidence(report.get("evidence"))
    if report.get("issues") != []:
        raise RealTritonFirstSlicePlanError("first-slice plan issues must be empty")
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_payloads() -> dict[str, Mapping[str, object]]:
    texts = {
        "real_triton_integration_admission_gate": build_real_triton_admission_report(),
        "real_triton_surface_gate_completion": build_surface_gate_completion_report(),
        "source_ingestion_quarantine_gate": build_source_ingestion_quarantine_report(),
        "admitting_source_ingestion_rfc": build_admitting_source_ingestion_rfc_report(),
        "bounded_source_buffer_api": build_bounded_source_buffer_api_report(),
        "source_ingestion_sandbox_implementation": (
            build_source_ingestion_sandbox_implementation_report()
        ),
        "parser_fuzz_negative_corpus_for_admitting_slice": (
            build_parser_fuzz_negative_corpus_report()
        ),
        "source_to_intent_research_source_runtime_smoke": (
            build_source_runtime_smoke_report()
        ),
        "source_to_intent_research_kernel_ingress_proof_bundle": (
            build_kernel_ingress_proof_bundle_report()
        ),
    }
    return {
        evidence_id: _json_payload(text, evidence_id)
        for evidence_id, text in texts.items()
    }


def _assert_supporting_payloads(payloads: Mapping[str, Mapping[str, object]]) -> None:
    admission = payloads["real_triton_integration_admission_gate"]
    if admission.get("admitted") is not False or admission.get("admission_status") != "blocked":
        raise RealTritonFirstSlicePlanError("first-slice admission gate drift")

    completion = payloads["real_triton_surface_gate_completion"]
    if completion.get("completion_status") != "complete":
        raise RealTritonFirstSlicePlanError("first-slice surface completion drift")
    if completion.get("all_surface_gates_non_admitting") is not True:
        raise RealTritonFirstSlicePlanError("first-slice surface admission drift")

    source_gate = payloads["source_ingestion_quarantine_gate"]
    if source_gate.get("gate_status") != "quarantine_only":
        raise RealTritonFirstSlicePlanError("first-slice source gate status drift")
    for field_name in (
        "direct_source_ingestion",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_runtime_plan",
        "python_import",
        "triton_jit_execution",
        "generated_artifact_execution",
    ):
        if source_gate.get(field_name) is not False:
            raise RealTritonFirstSlicePlanError(
                f"first-slice source gate {field_name} drift"
            )

    rfc = payloads["admitting_source_ingestion_rfc"]
    if rfc.get("proposal_status") != "accepted_requirements_only":
        raise RealTritonFirstSlicePlanError("first-slice RFC status drift")
    if rfc.get("implementation_status") != "not_implemented":
        raise RealTritonFirstSlicePlanError("first-slice RFC implementation drift")
    if rfc.get("admitted") is not False:
        raise RealTritonFirstSlicePlanError("first-slice RFC admission drift")
    if rfc.get("source_ingestion_admission_ready") is not False:
        raise RealTritonFirstSlicePlanError("first-slice RFC readiness drift")
    if tuple(_string_list(rfc.get("remaining_evidence"))) != (
        ADMITTING_SOURCE_INGESTION_RFC_REMAINING_EVIDENCE
    ):
        raise RealTritonFirstSlicePlanError("first-slice RFC remaining evidence drift")

    buffer_api = payloads["bounded_source_buffer_api"]
    if buffer_api.get("api_status") != "implemented_non_admitting":
        raise RealTritonFirstSlicePlanError("first-slice buffer API status drift")
    if buffer_api.get("direct_source_ingestion") is not False:
        raise RealTritonFirstSlicePlanError("first-slice buffer API admission drift")
    for field_name in (
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_runtime_plan",
    ):
        if buffer_api.get(field_name) is not False:
            raise RealTritonFirstSlicePlanError(
                f"first-slice buffer API {field_name} drift"
            )

    sandbox = payloads["source_ingestion_sandbox_implementation"]
    if sandbox.get("sandbox_status") != "implemented_non_admitting":
        raise RealTritonFirstSlicePlanError("first-slice sandbox status drift")
    for field_name in (
        "direct_source_ingestion",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_intent_plain_data",
        "source_to_runtime_plan",
    ):
        if sandbox.get(field_name) is not False:
            raise RealTritonFirstSlicePlanError(
                f"first-slice sandbox {field_name} drift"
            )

    negative_corpus = payloads["parser_fuzz_negative_corpus_for_admitting_slice"]
    if negative_corpus.get("corpus_status") != "complete_non_admitting":
        raise RealTritonFirstSlicePlanError("first-slice parser corpus status drift")
    if negative_corpus.get("required_rejection_coverage_complete") is not True:
        raise RealTritonFirstSlicePlanError("first-slice parser corpus coverage drift")
    for field_name in (
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_intent_plain_data",
        "source_to_runtime_plan",
    ):
        if negative_corpus.get(field_name) is not False:
            raise RealTritonFirstSlicePlanError(
                f"first-slice parser corpus {field_name} drift"
            )

    smoke = payloads["source_to_intent_research_source_runtime_smoke"]
    if smoke.get("status") != "PASS" or smoke.get("case_count") != 2:
        raise RealTritonFirstSlicePlanError("first-slice source smoke drift")
    if smoke.get("default_parser_status") != "default_parser_blocked":
        raise RealTritonFirstSlicePlanError("first-slice parser status drift")

    kernel = payloads["source_to_intent_research_kernel_ingress_proof_bundle"]
    if kernel.get("status") != "PASS" or kernel.get("artifact_count") != 15:
        raise RealTritonFirstSlicePlanError("first-slice kernel bundle drift")
    if tuple(_string_list(kernel.get("covered_operation_families"))) != (
        "elementwise",
        "matmul",
        "reduction",
        "softmax",
    ):
        raise RealTritonFirstSlicePlanError("first-slice operation coverage drift")


def _evidence_from_payload(
    evidence_id: str,
    payload: Mapping[str, object],
    contract_key: str,
    status_key: str,
) -> dict[str, object]:
    _validate_report_token(evidence_id, "evidence_id")
    contract = payload.get(contract_key)
    status = payload.get(status_key)
    if not isinstance(contract, str):
        raise RealTritonFirstSlicePlanError("first-slice evidence contract missing")
    if not isinstance(status, str):
        raise RealTritonFirstSlicePlanError("first-slice evidence status missing")
    _validate_report_token(contract, "contract")
    _validate_report_token(status, "status")
    return {
        "contract": contract,
        "digest": _digest_payload(payload),
        "evidence_id": evidence_id,
        "source_free": True,
        "status": status,
        "supports_plan": True,
    }


def _assert_evidence(value: object) -> None:
    if not isinstance(value, list):
        raise RealTritonFirstSlicePlanError("first-slice evidence must be list")
    if len(value) != len(REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_IDS):
        raise RealTritonFirstSlicePlanError("first-slice evidence count drift")
    evidence_ids = []
    statuses = []
    digests = []
    for item in value:
        if not isinstance(item, Mapping):
            raise RealTritonFirstSlicePlanError("first-slice evidence item invalid")
        if set(item) != _EVIDENCE_KEYS:
            raise RealTritonFirstSlicePlanError("first-slice evidence keys drift")
        evidence_id = item.get("evidence_id")
        status = item.get("status")
        contract = item.get("contract")
        digest = item.get("digest")
        if not isinstance(evidence_id, str) or not isinstance(status, str):
            raise RealTritonFirstSlicePlanError("first-slice evidence text invalid")
        if not isinstance(contract, str) or not isinstance(digest, str):
            raise RealTritonFirstSlicePlanError("first-slice evidence digest invalid")
        _validate_report_token(evidence_id, "evidence_id")
        _validate_report_token(status, "status")
        _validate_report_token(contract, "contract")
        if not _SHA256_RE.fullmatch(digest):
            raise RealTritonFirstSlicePlanError("first-slice evidence digest invalid")
        if item.get("source_free") is not True:
            raise RealTritonFirstSlicePlanError("first-slice evidence source flag drift")
        if item.get("supports_plan") is not True:
            raise RealTritonFirstSlicePlanError("first-slice evidence support drift")
        evidence_ids.append(evidence_id)
        statuses.append(status)
        digests.append(digest)
    if tuple(evidence_ids) != REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_IDS:
        raise RealTritonFirstSlicePlanError("first-slice evidence IDs drift")
    if tuple(statuses) != REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_EXPECTED_STATUS:
        raise RealTritonFirstSlicePlanError("first-slice evidence status drift")
    if len(digests) != len(set(digests)):
        raise RealTritonFirstSlicePlanError("first-slice evidence digests must be unique")


def _json_payload(text: str, evidence_id: str) -> Mapping[str, object]:
    _assert_text_is_source_free(text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RealTritonFirstSlicePlanError(f"{evidence_id} is not JSON") from exc
    if not isinstance(payload, Mapping):
        raise RealTritonFirstSlicePlanError(f"{evidence_id} must be object")
    return payload


def _digest_payload(payload: Mapping[str, object]) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _assert_string_sequence(value: object, expected: tuple[str, ...], field_name: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise RealTritonFirstSlicePlanError(f"first-slice {field_name} drift")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise RealTritonFirstSlicePlanError("first-slice expected string list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise RealTritonFirstSlicePlanError("first-slice string list item invalid")
        _validate_report_token(item, "list item")
        result.append(item)
    return result


def _validate_report_token(value: str, label: str) -> None:
    if not _REPORT_TOKEN_RE.fullmatch(value) or value in _FORBIDDEN_TOKENS:
        raise RealTritonFirstSlicePlanError(f"first-slice {label} is not report-safe")


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in lowered:
            raise RealTritonFirstSlicePlanError(
                f"first-slice plan contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
