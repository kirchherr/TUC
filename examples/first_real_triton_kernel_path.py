"""Emit the first real Triton-shaped kernel path proof report."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_ingestion_admission_gate import (
        SOURCE_INGESTION_ADMISSION_GATE_CONTRACT,
        assert_source_ingestion_admission_gate_report_contract,
    )
    from examples.source_ingestion_admission_gate import (
        build_report as build_source_ingestion_admission_gate_report,
    )
    from examples.source_ingestion_preclaim_acyclicity_gate import (
        SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_CONTRACT,
        assert_source_ingestion_preclaim_acyclicity_gate_report_contract,
    )
    from examples.source_ingestion_preclaim_acyclicity_gate import (
        build_report as build_source_ingestion_preclaim_acyclicity_gate_report,
    )
    from examples.source_to_intent_research_kernel_ingress import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        assert_kernel_ingress_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
    from examples.source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles import (  # noqa: E501
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT,
        assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles import (  # noqa: E501
        build_report as build_kernel_ingress_backend_equivalence_shape_profiles_report,
    )
    from examples.source_to_intent_research_kernel_ingress_evidence_gate import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_CONTRACT,
        assert_kernel_ingress_evidence_gate_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_evidence_gate import (
        build_gate_report as build_kernel_ingress_evidence_gate_report,
    )
    from examples.source_to_intent_research_kernel_ingress_proof_bundle import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CONTRACT,
        assert_kernel_ingress_proof_bundle_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_proof_bundle import (
        build_report as build_kernel_ingress_proof_bundle_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_kernel_ingress_runtime_matrix_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_ingestion_admission_gate import (  # type: ignore[no-redef]
        SOURCE_INGESTION_ADMISSION_GATE_CONTRACT,
        assert_source_ingestion_admission_gate_report_contract,
    )
    from source_ingestion_admission_gate import (
        build_report as build_source_ingestion_admission_gate_report,
    )
    from source_ingestion_preclaim_acyclicity_gate import (  # type: ignore[no-redef]
        SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_CONTRACT,
        assert_source_ingestion_preclaim_acyclicity_gate_report_contract,
    )
    from source_ingestion_preclaim_acyclicity_gate import (
        build_report as build_source_ingestion_preclaim_acyclicity_gate_report,
    )
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        assert_kernel_ingress_report_contract,
    )
    from source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
    from source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles import (  # type: ignore[no-redef]  # noqa: E501
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT,
        assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract,
    )
    from source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles import (  # noqa: E501
        build_report as build_kernel_ingress_backend_equivalence_shape_profiles_report,
    )
    from source_to_intent_research_kernel_ingress_evidence_gate import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_CONTRACT,
        assert_kernel_ingress_evidence_gate_report_contract,
    )
    from source_to_intent_research_kernel_ingress_evidence_gate import (
        build_gate_report as build_kernel_ingress_evidence_gate_report,
    )
    from source_to_intent_research_kernel_ingress_proof_bundle import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CONTRACT,
        assert_kernel_ingress_proof_bundle_report_contract,
    )
    from source_to_intent_research_kernel_ingress_proof_bundle import (
        build_report as build_kernel_ingress_proof_bundle_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_kernel_ingress_runtime_matrix_report,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
)

FIRST_REAL_TRITON_KERNEL_PATH_REPORT_SCHEMA_VERSION = (
    "tuc.first_real_triton_kernel_path_report.v0"
)
FIRST_REAL_TRITON_KERNEL_PATH_CONTRACT = (
    "first_real_triton_kernel_path.digest_bound.v0"
)
FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_ID = "first_real_triton_kernel_path"
FIRST_REAL_TRITON_KERNEL_PATH_CASE_ID = "research_module_mvp_pipeline"
FIRST_REAL_TRITON_KERNEL_PATH_KERNEL_NAME = "mvp_pipeline"
FIRST_REAL_TRITON_KERNEL_PATH_SOURCE_BOUNDARY = (
    "module_shaped_triton_source_buffer_to_source_intent_to_trusted_runtime_evidence"
)
FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_POLICY = "digest_only_source_free"
FIRST_REAL_TRITON_KERNEL_PATH_STATUS = "PASS"
FIRST_REAL_TRITON_KERNEL_PATH_BACKEND_SEQUENCE = (
    "linear-sim",
    "vector-sim",
    "vector-sim",
    "vector-sim",
)
FIRST_REAL_TRITON_KERNEL_PATH_OPERATION_FAMILIES = (
    "elementwise",
    "matmul",
    "reduction",
    "softmax",
)
FIRST_REAL_TRITON_KERNEL_PATH_TERMINAL_OUTPUTS = ("stable",)
FIRST_REAL_TRITON_KERNEL_PATH_TRACE_STEP_COUNT = 4
FIRST_REAL_TRITON_KERNEL_PATH_OBSERVED_PATH = (
    "bounded_module_source_buffer",
    "controlled_kernel_extraction",
    "source_intent_plain_data_reintake",
    "compute_graph_compile",
    "trusted_prototype_runtime_execution",
    "backend_equivalence_metadata_check",
    "source_ingestion_admission_remains_closed",
)
FIRST_REAL_TRITON_KERNEL_PATH_PROVEN_CLAIMS = (
    "single_mvp_pipeline_kernel_path_bound",
    "mvp_operation_family_runtime_path_bound",
    "source_intent_plain_data_reintake_bound",
    "capability_selected_trusted_runtime_execution_bound",
    "backend_equivalence_metadata_bound",
    "admission_gate_remains_fail_closed",
)
FIRST_REAL_TRITON_KERNEL_PATH_BLOCKED_CLAIMS = (
    "arbitrary_triton_source_ingestion",
    "production_parser",
    "native_backend_execution",
    "native_performance_parity",
    "cuda_replacement",
    "runtime_handle_residency",
)
FIRST_REAL_TRITON_KERNEL_PATH_BLOCKED_SURFACES = (
    "direct_source_ingestion",
    "default_source_parser",
    "frontend_package_import",
    "plugin_discovery",
    "triton_jit_execution",
    "device_access",
    "generated_artifact_execution",
    "native_backend_execution",
    "raw_tensor_serialization",
)
_REQUIRED_BINDINGS = (
    (
        "source_to_intent_research_kernel_ingress",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        "PASS",
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_matrix",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        "PASS",
    ),
    (
        "source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT,
        "PASS",
    ),
    (
        "source_to_intent_research_kernel_ingress_proof_bundle",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CONTRACT,
        "PASS",
    ),
    (
        "source_to_intent_research_kernel_ingress_evidence_gate",
        "text_gate",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_CONTRACT,
        "PASS",
    ),
    (
        "source_ingestion_preclaim_acyclicity_gate",
        "json_report",
        SOURCE_INGESTION_PRECLAIM_ACYCLICITY_GATE_CONTRACT,
        "PASS",
    ),
    (
        "source_ingestion_admission_gate",
        "json_report",
        SOURCE_INGESTION_ADMISSION_GATE_CONTRACT,
        "blocked_missing_maintainer_security_review_approval",
    ),
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "backend_sequence",
        "blocked_claims",
        "blocked_surfaces",
        "case_id",
        "default_parser_status",
        "evidence_binding_count",
        "evidence_bindings",
        "evidence_policy",
        "kernel_name",
        "observed_path",
        "operation_families",
        "parser_status",
        "path_contract",
        "proof_id",
        "proven_claims",
        "schema_version",
        "source_boundary",
        "status",
        "terminal_outputs",
        "trace_step_count",
    }
)
_BINDING_KEYS = frozenset(
    {"artifact_id", "artifact_kind", "contract", "digest", "source_free", "status"}
)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
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


class FirstRealTritonKernelPathError(AssertionError):
    """Raised when first real Triton-shaped kernel path evidence drifts."""


def build_first_real_triton_kernel_path_report() -> dict[str, object]:
    """Return digest-bound evidence for the current MVP Kernel Ingress path."""

    texts = _build_texts()
    payloads = _build_payloads(texts)
    _assert_supporting_payloads(payloads, texts)
    bindings = [
        _build_binding(artifact_id, artifact_kind, contract, status, texts[artifact_id])
        for artifact_id, artifact_kind, contract, status in _REQUIRED_BINDINGS
    ]
    report: dict[str, object] = {
        "backend_sequence": list(FIRST_REAL_TRITON_KERNEL_PATH_BACKEND_SEQUENCE),
        "blocked_claims": list(FIRST_REAL_TRITON_KERNEL_PATH_BLOCKED_CLAIMS),
        "blocked_surfaces": list(FIRST_REAL_TRITON_KERNEL_PATH_BLOCKED_SURFACES),
        "case_id": FIRST_REAL_TRITON_KERNEL_PATH_CASE_ID,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "evidence_binding_count": len(bindings),
        "evidence_bindings": bindings,
        "evidence_policy": FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_POLICY,
        "kernel_name": FIRST_REAL_TRITON_KERNEL_PATH_KERNEL_NAME,
        "observed_path": list(FIRST_REAL_TRITON_KERNEL_PATH_OBSERVED_PATH),
        "operation_families": list(FIRST_REAL_TRITON_KERNEL_PATH_OPERATION_FAMILIES),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "path_contract": FIRST_REAL_TRITON_KERNEL_PATH_CONTRACT,
        "proof_id": FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_ID,
        "proven_claims": list(FIRST_REAL_TRITON_KERNEL_PATH_PROVEN_CLAIMS),
        "schema_version": FIRST_REAL_TRITON_KERNEL_PATH_REPORT_SCHEMA_VERSION,
        "source_boundary": FIRST_REAL_TRITON_KERNEL_PATH_SOURCE_BOUNDARY,
        "status": FIRST_REAL_TRITON_KERNEL_PATH_STATUS,
        "terminal_outputs": list(FIRST_REAL_TRITON_KERNEL_PATH_TERMINAL_OUTPUTS),
        "trace_step_count": FIRST_REAL_TRITON_KERNEL_PATH_TRACE_STEP_COUNT,
    }
    assert_first_real_triton_kernel_path_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the first real Triton-shaped path."""

    return json.dumps(
        build_first_real_triton_kernel_path_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_first_real_triton_kernel_path_report_contract(
    report: object,
) -> None:
    """Fail closed unless first real Triton-shaped path evidence matches v0."""

    if not isinstance(report, Mapping):
        raise FirstRealTritonKernelPathError("first real Triton path report must be object")
    if set(report) != _TOP_LEVEL_KEYS:
        raise FirstRealTritonKernelPathError("first real Triton path top-level keys drift")
    expected = {
        "backend_sequence": list(FIRST_REAL_TRITON_KERNEL_PATH_BACKEND_SEQUENCE),
        "blocked_claims": list(FIRST_REAL_TRITON_KERNEL_PATH_BLOCKED_CLAIMS),
        "blocked_surfaces": list(FIRST_REAL_TRITON_KERNEL_PATH_BLOCKED_SURFACES),
        "case_id": FIRST_REAL_TRITON_KERNEL_PATH_CASE_ID,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "evidence_binding_count": len(_REQUIRED_BINDINGS),
        "evidence_policy": FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_POLICY,
        "kernel_name": FIRST_REAL_TRITON_KERNEL_PATH_KERNEL_NAME,
        "observed_path": list(FIRST_REAL_TRITON_KERNEL_PATH_OBSERVED_PATH),
        "operation_families": list(FIRST_REAL_TRITON_KERNEL_PATH_OPERATION_FAMILIES),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "path_contract": FIRST_REAL_TRITON_KERNEL_PATH_CONTRACT,
        "proof_id": FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_ID,
        "proven_claims": list(FIRST_REAL_TRITON_KERNEL_PATH_PROVEN_CLAIMS),
        "schema_version": FIRST_REAL_TRITON_KERNEL_PATH_REPORT_SCHEMA_VERSION,
        "source_boundary": FIRST_REAL_TRITON_KERNEL_PATH_SOURCE_BOUNDARY,
        "status": FIRST_REAL_TRITON_KERNEL_PATH_STATUS,
        "terminal_outputs": list(FIRST_REAL_TRITON_KERNEL_PATH_TERMINAL_OUTPUTS),
        "trace_step_count": FIRST_REAL_TRITON_KERNEL_PATH_TRACE_STEP_COUNT,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise FirstRealTritonKernelPathError(f"first real Triton path {key} drift")
    _assert_bindings(report.get("evidence_bindings"))
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_texts() -> dict[str, str]:
    return {
        "source_to_intent_research_kernel_ingress": build_kernel_ingress_report(),
        "source_to_intent_research_kernel_ingress_runtime_matrix": (
            build_kernel_ingress_runtime_matrix_report()
        ),
        "source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles": (
            build_kernel_ingress_backend_equivalence_shape_profiles_report()
        ),
        "source_to_intent_research_kernel_ingress_proof_bundle": (
            build_kernel_ingress_proof_bundle_report()
        ),
        "source_to_intent_research_kernel_ingress_evidence_gate": (
            build_kernel_ingress_evidence_gate_report()
        ),
        "source_ingestion_preclaim_acyclicity_gate": (
            build_source_ingestion_preclaim_acyclicity_gate_report()
        ),
        "source_ingestion_admission_gate": (
            build_source_ingestion_admission_gate_report()
        ),
    }


def _build_payloads(texts: Mapping[str, str]) -> dict[str, Mapping[str, object]]:
    payloads: dict[str, Mapping[str, object]] = {}
    for artifact_id, text in texts.items():
        _assert_text_is_source_free(text)
        if artifact_id == "source_to_intent_research_kernel_ingress_evidence_gate":
            continue
        payloads[artifact_id] = _json_payload(text, artifact_id)
    return payloads


def _assert_supporting_payloads(
    payloads: Mapping[str, Mapping[str, object]],
    texts: Mapping[str, str],
) -> None:
    kernel_ingress = payloads["source_to_intent_research_kernel_ingress"]
    assert_kernel_ingress_report_contract(kernel_ingress)
    runtime_matrix = payloads["source_to_intent_research_kernel_ingress_runtime_matrix"]
    assert_kernel_ingress_runtime_matrix_report_contract(runtime_matrix)
    shape_profiles = payloads[
        "source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles"
    ]
    assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract(
        shape_profiles
    )
    proof_bundle = payloads["source_to_intent_research_kernel_ingress_proof_bundle"]
    assert_kernel_ingress_proof_bundle_report_contract(proof_bundle)
    evidence_gate = texts["source_to_intent_research_kernel_ingress_evidence_gate"]
    assert_kernel_ingress_evidence_gate_report_contract(evidence_gate)
    preclaim = payloads["source_ingestion_preclaim_acyclicity_gate"]
    assert_source_ingestion_preclaim_acyclicity_gate_report_contract(preclaim)
    admission = payloads["source_ingestion_admission_gate"]
    assert_source_ingestion_admission_gate_report_contract(admission)

    _assert_mvp_case(_case_by_id(kernel_ingress, FIRST_REAL_TRITON_KERNEL_PATH_CASE_ID))
    _assert_mvp_case(_case_by_id(runtime_matrix, FIRST_REAL_TRITON_KERNEL_PATH_CASE_ID))
    if shape_profiles.get("status") != "PASS":
        raise FirstRealTritonKernelPathError(
            "first real Triton path shape-profile status drift"
        )
    if proof_bundle.get("status") != "PASS":
        raise FirstRealTritonKernelPathError(
            "first real Triton path proof-bundle status drift"
        )
    if preclaim.get("gate_status") != "PASS":
        raise FirstRealTritonKernelPathError("first real Triton path preclaim drift")
    if admission.get("direct_source_ingestion") is not False:
        raise FirstRealTritonKernelPathError(
            "first real Triton path admission surface drift"
        )
    if admission.get("source_ingestion_admission_ready") is not False:
        raise FirstRealTritonKernelPathError(
            "first real Triton path admission readiness drift"
        )


def _assert_mvp_case(case: Mapping[str, object]) -> None:
    expected = {
        "backend_sequence": list(FIRST_REAL_TRITON_KERNEL_PATH_BACKEND_SEQUENCE),
        "case_id": FIRST_REAL_TRITON_KERNEL_PATH_CASE_ID,
        "kernel_name": FIRST_REAL_TRITON_KERNEL_PATH_KERNEL_NAME,
        "operation_families": list(FIRST_REAL_TRITON_KERNEL_PATH_OPERATION_FAMILIES),
        "terminal_outputs": list(FIRST_REAL_TRITON_KERNEL_PATH_TERMINAL_OUTPUTS),
        "trace_step_count": FIRST_REAL_TRITON_KERNEL_PATH_TRACE_STEP_COUNT,
    }
    for key, expected_value in expected.items():
        if case.get(key) != expected_value:
            raise FirstRealTritonKernelPathError(
                f"first real Triton path MVP case {key} drift"
            )


def _case_by_id(report: Mapping[str, object], case_id: str) -> Mapping[str, object]:
    cases = report.get("cases")
    if not isinstance(cases, list):
        raise FirstRealTritonKernelPathError("first real Triton path cases drift")
    for case in cases:
        if isinstance(case, Mapping) and case.get("case_id") == case_id:
            return case
    raise FirstRealTritonKernelPathError("first real Triton path MVP case missing")


def _build_binding(
    artifact_id: str,
    artifact_kind: str,
    contract: str,
    status: str,
    text: str,
) -> dict[str, object]:
    return {
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "contract": contract,
        "digest": _digest(text),
        "source_free": True,
        "status": status,
    }


def _assert_bindings(bindings: object) -> None:
    if not isinstance(bindings, list):
        raise FirstRealTritonKernelPathError("first real Triton path bindings drift")
    if len(bindings) != len(_REQUIRED_BINDINGS):
        raise FirstRealTritonKernelPathError("first real Triton path binding count drift")
    observed_ids = []
    for binding, expected in zip(bindings, _REQUIRED_BINDINGS, strict=True):
        observed_ids.append(_assert_binding(binding, expected))
    if tuple(observed_ids) != tuple(item[0] for item in _REQUIRED_BINDINGS):
        raise FirstRealTritonKernelPathError("first real Triton path binding order drift")


def _assert_binding(
    binding: object,
    expected: tuple[str, str, str, str],
) -> str:
    if not isinstance(binding, Mapping):
        raise FirstRealTritonKernelPathError("first real Triton path binding drift")
    if set(binding) != _BINDING_KEYS:
        raise FirstRealTritonKernelPathError("first real Triton path binding keys drift")
    artifact_id, artifact_kind, contract, status = expected
    expected_values = {
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "contract": contract,
        "source_free": True,
        "status": status,
    }
    for key, expected_value in expected_values.items():
        if binding.get(key) != expected_value:
            raise FirstRealTritonKernelPathError(
                f"first real Triton path binding {key} drift"
            )
    digest = binding.get("digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise FirstRealTritonKernelPathError("first real Triton path digest drift")
    return artifact_id


def _json_payload(text: str, evidence_id: str) -> Mapping[str, object]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FirstRealTritonKernelPathError(
            f"first real Triton path {evidence_id} JSON drift"
        ) from exc
    if not isinstance(payload, Mapping):
        raise FirstRealTritonKernelPathError(
            f"first real Triton path {evidence_id} payload drift"
        )
    return payload


def _assert_text_is_source_free(text: str) -> None:
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise FirstRealTritonKernelPathError(
                "first real Triton path source/value material leaked"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
