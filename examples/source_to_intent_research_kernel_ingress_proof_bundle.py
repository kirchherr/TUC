"""Emit a digest-only review bundle for Kernel Ingress research evidence."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_kernel_ingress import (
        assert_kernel_ingress_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
    from examples.source_to_intent_research_kernel_ingress_backend_equivalence import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT,
        assert_kernel_ingress_backend_equivalence_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_backend_equivalence import (
        build_report as build_kernel_ingress_backend_equivalence_report,
    )
    from examples.source_to_intent_research_kernel_ingress_boundary_budget import (
        assert_kernel_ingress_boundary_budget_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_boundary_budget import (
        build_report as build_kernel_ingress_boundary_budget_report,
    )
    from examples.source_to_intent_research_kernel_ingress_conformance_gate import (
        build_gate_report as build_kernel_ingress_conformance_gate_report,
    )
    from examples.source_to_intent_research_kernel_ingress_diagnostics import (
        build_report as build_kernel_ingress_diagnostics_report,
    )
    from examples.source_to_intent_research_kernel_ingress_idiom_alignment import (
        assert_kernel_ingress_idiom_alignment_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_idiom_alignment import (
        build_report as build_kernel_ingress_idiom_alignment_report,
    )
    from examples.source_to_intent_research_kernel_ingress_rejection_coverage import (
        assert_kernel_ingress_rejection_coverage_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_rejection_coverage import (
        build_report as build_kernel_ingress_rejection_coverage_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_backend_alignment import (
        assert_kernel_ingress_runtime_backend_alignment_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_backend_alignment import (
        build_report as build_kernel_ingress_runtime_backend_alignment_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_coverage_policy import (
        assert_kernel_ingress_runtime_coverage_policy_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_coverage_policy import (
        build_report as build_kernel_ingress_runtime_coverage_policy_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT,
        assert_kernel_ingress_runtime_evidence_bundle_index_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (
        build_report as build_kernel_ingress_runtime_evidence_bundle_index_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_kernel_ingress_runtime_matrix_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_step_trace import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT,
        assert_kernel_ingress_runtime_step_trace_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_step_trace import (
        build_report as build_kernel_ingress_runtime_step_trace_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        assert_kernel_ingress_report_contract,
    )
    from source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
    from source_to_intent_research_kernel_ingress_backend_equivalence import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT,
        assert_kernel_ingress_backend_equivalence_report_contract,
    )
    from source_to_intent_research_kernel_ingress_backend_equivalence import (
        build_report as build_kernel_ingress_backend_equivalence_report,
    )
    from source_to_intent_research_kernel_ingress_boundary_budget import (  # type: ignore[no-redef]
        assert_kernel_ingress_boundary_budget_report_contract,
    )
    from source_to_intent_research_kernel_ingress_boundary_budget import (
        build_report as build_kernel_ingress_boundary_budget_report,
    )
    from source_to_intent_research_kernel_ingress_conformance_gate import (
        build_gate_report as build_kernel_ingress_conformance_gate_report,
    )
    from source_to_intent_research_kernel_ingress_diagnostics import (
        build_report as build_kernel_ingress_diagnostics_report,
    )
    from source_to_intent_research_kernel_ingress_idiom_alignment import (  # type: ignore[no-redef]
        assert_kernel_ingress_idiom_alignment_report_contract,
    )
    from source_to_intent_research_kernel_ingress_idiom_alignment import (
        build_report as build_kernel_ingress_idiom_alignment_report,
    )
    from source_to_intent_research_kernel_ingress_rejection_coverage import (  # type: ignore[no-redef]
        assert_kernel_ingress_rejection_coverage_report_contract,
    )
    from source_to_intent_research_kernel_ingress_rejection_coverage import (
        build_report as build_kernel_ingress_rejection_coverage_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_backend_alignment import (  # type: ignore[no-redef]
        assert_kernel_ingress_runtime_backend_alignment_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_backend_alignment import (
        build_report as build_kernel_ingress_runtime_backend_alignment_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_coverage_policy import (  # type: ignore[no-redef]
        assert_kernel_ingress_runtime_coverage_policy_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_coverage_policy import (
        build_report as build_kernel_ingress_runtime_coverage_policy_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT,
        assert_kernel_ingress_runtime_evidence_bundle_index_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (
        build_report as build_kernel_ingress_runtime_evidence_bundle_index_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (  # type: ignore[no-redef]
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_kernel_ingress_runtime_matrix_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_step_trace import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT,
        assert_kernel_ingress_runtime_step_trace_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_step_trace import (
        build_report as build_kernel_ingress_runtime_step_trace_report,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_proof_bundle_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CONTRACT = (
    "source_to_intent_research_kernel_ingress_proof_bundle.review.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_ARTIFACT_POLICY = (
    "digest_only_source_free"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CLAIM = (
    "realistic_triton_module_ingress_research_slice"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_SOURCE_BOUNDARY = (
    "triton_module_source_buffer_to_source_intent_to_runtime_metadata_only"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_BLOCKED_CLAIMS = (
    "general_triton_source_ingestion",
    "native_performance_claim",
    "production_parser",
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_REVIEW_CLAIMS = (
    "conformance_bound",
    "boundary_budget_bound",
    "rejection_coverage_bound",
    "diagnostics_bound",
    "idiom_scope_bound",
    "kernel_ingress_runtime_e2e",
    "runtime_matrix_bound",
    "runtime_step_trace_bound",
    "runtime_evidence_bundle_index_bound",
    "runtime_backend_equivalence_bound",
    "runtime_coverage_policy_bound",
    "runtime_backend_alignment_bound",
    "source_free_metadata_only",
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"module_source":',
    "python_source",
    '"raw_source":',
    "raw_tensor_value",
    "secret.txt",
    "source_intent_payload",
    "tl.dot",
    "tl.store",
)

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "accepted_kernel_names",
        "accepted_source_names",
        "artifact_count",
        "artifact_policy",
        "artifacts",
        "blocked_claims",
        "bundle_contract",
        "claim",
        "covered_operation_families",
        "default_parser_status",
        "parser_status",
        "required_artifacts",
        "review_claims",
        "schema_version",
        "source_boundary",
        "status",
    }
)
_ARTIFACT_KEYS = frozenset(
    {"artifact_id", "artifact_kind", "contract", "digest", "status"}
)
_REQUIRED_ARTIFACTS = (
    (
        "source_to_intent_research_kernel_ingress",
        "json_report",
        "source_to_intent_research_kernel_ingress.e2e.v0",
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_matrix",
        "json_report",
        "source_to_intent_research_kernel_ingress_runtime_matrix.execution.v0",
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_step_trace",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT,
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT,
    ),
    (
        "source_to_intent_research_kernel_ingress_backend_equivalence",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT,
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_coverage_policy",
        "json_report",
        "source_to_intent_research_kernel_ingress_runtime_coverage_policy.review.v0",
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_backend_alignment",
        "json_report",
        "source_to_intent_research_kernel_ingress_runtime_backend_alignment.trusted_executor.v0",
    ),
    (
        "source_to_intent_research_kernel_ingress_boundary_budget",
        "json_report",
        "source_to_intent_research_kernel_ingress_boundary_budget.security.v0",
    ),
    (
        "source_to_intent_research_kernel_ingress_rejection_coverage",
        "json_report",
        "source_to_intent_research_kernel_ingress_rejection_coverage.security.v0",
    ),
    (
        "source_to_intent_research_kernel_ingress_diagnostics",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT,
    ),
    (
        "source_to_intent_research_kernel_ingress_conformance_gate",
        "text_gate",
        "source_to_intent_research_kernel_ingress_conformance_gate.ci.v0",
    ),
    (
        "source_to_intent_research_kernel_ingress_idiom_alignment",
        "json_report",
        "source_to_intent_research_kernel_ingress_idiom_alignment.scope.v0",
    ),
)
_ACCEPTED_SOURCE_NAMES = (
    "research_matmul_elementwise",
    "research_softmax_reduction",
    "research_matmul_reduction",
    "research_mvp_pipeline",
)
_ACCEPTED_KERNEL_NAMES = (
    "matmul_elementwise",
    "softmax_reduction",
    "matmul_reduction",
    "mvp_pipeline",
)
_COVERED_OPERATION_FAMILIES = (
    "elementwise",
    "matmul",
    "reduction",
    "softmax",
)


def build_kernel_ingress_proof_bundle_report() -> dict[str, object]:
    """Return a source-free digest bundle for Kernel Ingress review."""

    artifact_texts = {
        "source_to_intent_research_kernel_ingress": build_kernel_ingress_report(),
        "source_to_intent_research_kernel_ingress_runtime_matrix": (
            build_kernel_ingress_runtime_matrix_report()
        ),
        "source_to_intent_research_kernel_ingress_runtime_step_trace": (
            build_kernel_ingress_runtime_step_trace_report()
        ),
        "source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index": (
            build_kernel_ingress_runtime_evidence_bundle_index_report()
        ),
        "source_to_intent_research_kernel_ingress_backend_equivalence": (
            build_kernel_ingress_backend_equivalence_report()
        ),
        "source_to_intent_research_kernel_ingress_runtime_coverage_policy": (
            build_kernel_ingress_runtime_coverage_policy_report()
        ),
        "source_to_intent_research_kernel_ingress_runtime_backend_alignment": (
            build_kernel_ingress_runtime_backend_alignment_report()
        ),
        "source_to_intent_research_kernel_ingress_boundary_budget": (
            build_kernel_ingress_boundary_budget_report()
        ),
        "source_to_intent_research_kernel_ingress_rejection_coverage": (
            build_kernel_ingress_rejection_coverage_report()
        ),
        "source_to_intent_research_kernel_ingress_diagnostics": (
            build_kernel_ingress_diagnostics_report()
        ),
        "source_to_intent_research_kernel_ingress_conformance_gate": (
            build_kernel_ingress_conformance_gate_report()
        ),
        "source_to_intent_research_kernel_ingress_idiom_alignment": (
            build_kernel_ingress_idiom_alignment_report()
        ),
    }
    _assert_artifact_payloads(artifact_texts)
    artifacts = [
        {
            "artifact_id": artifact_id,
            "artifact_kind": artifact_kind,
            "contract": contract,
            "digest": _digest(artifact_texts[artifact_id]),
            "status": "accepted",
        }
        for artifact_id, artifact_kind, contract in _REQUIRED_ARTIFACTS
    ]
    report: dict[str, object] = {
        "accepted_kernel_names": list(_ACCEPTED_KERNEL_NAMES),
        "accepted_source_names": list(_ACCEPTED_SOURCE_NAMES),
        "artifact_count": len(artifacts),
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_ARTIFACT_POLICY
        ),
        "artifacts": artifacts,
        "blocked_claims": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_BLOCKED_CLAIMS
        ),
        "bundle_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CONTRACT
        ),
        "claim": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CLAIM,
        "covered_operation_families": list(_COVERED_OPERATION_FAMILIES),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "required_artifacts": [artifact[0] for artifact in _REQUIRED_ARTIFACTS],
        "review_claims": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_REVIEW_CLAIMS
        ),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_SOURCE_BOUNDARY
        ),
        "status": "PASS",
    }
    assert_kernel_ingress_proof_bundle_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the Kernel Ingress proof bundle."""

    return json.dumps(
        build_kernel_ingress_proof_bundle_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_kernel_ingress_proof_bundle_report_contract(report: object) -> None:
    """Fail closed unless the Kernel Ingress proof bundle matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress proof bundle report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "accepted_kernel_names": list(_ACCEPTED_KERNEL_NAMES),
        "accepted_source_names": list(_ACCEPTED_SOURCE_NAMES),
        "artifact_count": len(_REQUIRED_ARTIFACTS),
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_ARTIFACT_POLICY
        ),
        "blocked_claims": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_BLOCKED_CLAIMS
        ),
        "bundle_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CONTRACT
        ),
        "claim": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CLAIM,
        "covered_operation_families": list(_COVERED_OPERATION_FAMILIES),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "required_artifacts": [artifact[0] for artifact in _REQUIRED_ARTIFACTS],
        "review_claims": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_REVIEW_CLAIMS
        ),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_SOURCE_BOUNDARY
        ),
        "status": "PASS",
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"kernel ingress proof bundle {key} contract drift")
    artifacts = report["artifacts"]
    if not isinstance(artifacts, list):
        raise ValueError("kernel ingress proof bundle artifacts drift")
    observed_ids = []
    for index, artifact in enumerate(artifacts):
        observed_ids.append(_assert_artifact_contract(index, artifact))
    if tuple(observed_ids) != tuple(artifact[0] for artifact in _REQUIRED_ARTIFACTS):
        raise ValueError("kernel ingress proof bundle artifact order drift")
    _assert_report_is_source_free(report)


def _assert_artifact_payloads(artifact_texts: Mapping[str, str]) -> None:
    ingress = json.loads(artifact_texts["source_to_intent_research_kernel_ingress"])
    assert_kernel_ingress_report_contract(ingress)
    runtime_matrix = json.loads(
        artifact_texts["source_to_intent_research_kernel_ingress_runtime_matrix"]
    )
    assert_kernel_ingress_runtime_matrix_report_contract(runtime_matrix)
    runtime_step_trace = json.loads(
        artifact_texts[
            "source_to_intent_research_kernel_ingress_runtime_step_trace"
        ]
    )
    assert_kernel_ingress_runtime_step_trace_report_contract(runtime_step_trace)
    runtime_evidence_bundle_index = json.loads(
        artifact_texts[
            "source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index"
        ]
    )
    assert_kernel_ingress_runtime_evidence_bundle_index_report_contract(
        runtime_evidence_bundle_index
    )
    backend_equivalence = json.loads(
        artifact_texts[
            "source_to_intent_research_kernel_ingress_backend_equivalence"
        ]
    )
    assert_kernel_ingress_backend_equivalence_report_contract(backend_equivalence)
    runtime_coverage_policy = json.loads(
        artifact_texts[
            "source_to_intent_research_kernel_ingress_runtime_coverage_policy"
        ]
    )
    assert_kernel_ingress_runtime_coverage_policy_report_contract(
        runtime_coverage_policy
    )
    runtime_backend_alignment = json.loads(
        artifact_texts[
            "source_to_intent_research_kernel_ingress_runtime_backend_alignment"
        ]
    )
    assert_kernel_ingress_runtime_backend_alignment_report_contract(
        runtime_backend_alignment
    )
    boundary_budget = json.loads(
        artifact_texts["source_to_intent_research_kernel_ingress_boundary_budget"]
    )
    assert_kernel_ingress_boundary_budget_report_contract(boundary_budget)
    rejection_coverage = json.loads(
        artifact_texts["source_to_intent_research_kernel_ingress_rejection_coverage"]
    )
    assert_kernel_ingress_rejection_coverage_report_contract(rejection_coverage)
    diagnostics = json.loads(
        artifact_texts["source_to_intent_research_kernel_ingress_diagnostics"]
    )
    _assert_kernel_ingress_diagnostics_contract(diagnostics)
    conformance = artifact_texts[
        "source_to_intent_research_kernel_ingress_conformance_gate"
    ]
    _assert_kernel_ingress_conformance_bound(conformance)
    idiom_alignment = json.loads(
        artifact_texts["source_to_intent_research_kernel_ingress_idiom_alignment"]
    )
    assert_kernel_ingress_idiom_alignment_report_contract(idiom_alignment)


def _assert_kernel_ingress_diagnostics_contract(report: object) -> None:
    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress proof bundle diagnostics must be object")
    expected_values = {
        "accepted_case_count": 4,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "diagnostics_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT
        ),
        "ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "rejected_case_count": 5,
        "rejection_reasons": sorted(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS
        ),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_SCHEMA_VERSION
        ),
    }
    for key, expected in expected_values.items():
        if report.get(key) != expected:
            raise ValueError(f"kernel ingress proof bundle diagnostics {key} drift")
    cases = report.get("cases")
    if not isinstance(cases, list) or len(cases) != 9:
        raise ValueError("kernel ingress proof bundle diagnostics cases drift")
    accepted = [case for case in cases if case.get("outcome") == "accepted"]
    if [case.get("source_name") for case in accepted] != list(_ACCEPTED_SOURCE_NAMES):
        raise ValueError("kernel ingress proof bundle accepted source drift")
    if [case.get("kernel_name") for case in accepted] != list(_ACCEPTED_KERNEL_NAMES):
        raise ValueError("kernel ingress proof bundle accepted kernel drift")
    _assert_text_is_source_free(json.dumps(report, sort_keys=True, separators=(",", ":")))


def _assert_kernel_ingress_conformance_bound(text: str) -> None:
    if not isinstance(text, str):
        raise ValueError("kernel ingress proof bundle conformance must be text")
    required_fragments = (
        'source_intent_frontend_conformance = "passed"',
        (
            'ingress_sources = "research_matmul_elementwise,'
            'research_softmax_reduction,research_matmul_reduction,'
            'research_mvp_pipeline"'
        ),
        (
            'kernel_names = "matmul_elementwise,softmax_reduction,'
            'matmul_reduction,mvp_pipeline"'
        ),
        'status = "PASS"',
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise ValueError("kernel ingress proof bundle conformance drift")
    _assert_text_is_source_free(text)


def _assert_artifact_contract(index: int, artifact: object) -> str:
    if not isinstance(artifact, Mapping):
        raise ValueError("kernel ingress proof bundle artifact must be object")
    _assert_exact_keys("artifact", artifact, _ARTIFACT_KEYS)
    expected_id, expected_kind, expected_contract = _REQUIRED_ARTIFACTS[index]
    expected_values = {
        "artifact_id": expected_id,
        "artifact_kind": expected_kind,
        "contract": expected_contract,
        "status": "accepted",
    }
    for key, expected in expected_values.items():
        if artifact[key] != expected:
            raise ValueError(f"kernel ingress proof bundle {key} contract drift")
    digest = artifact["digest"]
    if not isinstance(digest, str) or not _SHA256_DIGEST_PATTERN.fullmatch(digest):
        raise ValueError("kernel ingress proof bundle digest drift")
    return expected_id


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"kernel ingress proof bundle {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError("kernel ingress proof bundle report is not JSON data") from exc
    _assert_text_is_source_free(text)


def _assert_text_is_source_free(text: str) -> None:
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress proof bundle contains forbidden source or value material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
