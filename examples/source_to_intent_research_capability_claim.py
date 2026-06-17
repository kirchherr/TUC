"""Emit the current Source-to-Intent research capability claim."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_evidence_gate import (
        SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE_CONTRACT,
    )
    from examples.source_to_intent_research_evidence_gate import (
        build_gate_report as build_research_evidence_gate_report,
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
    from examples.source_to_intent_research_kernel_ingress_runtime_backend_alignment import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_CONTRACT,
        assert_kernel_ingress_runtime_backend_alignment_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_backend_alignment import (
        build_report as build_kernel_ingress_runtime_backend_alignment_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_coverage_policy import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT,
        assert_kernel_ingress_runtime_coverage_policy_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_coverage_policy import (
        build_report as build_kernel_ingress_runtime_coverage_policy_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_kernel_ingress_runtime_matrix_report,
    )
    from examples.source_to_intent_research_proof_bundle import (
        SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_CONTRACT,
        assert_proof_bundle_report_contract,
    )
    from examples.source_to_intent_research_proof_bundle import (
        build_report as build_research_proof_bundle_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_evidence_gate import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE_CONTRACT,
    )
    from source_to_intent_research_evidence_gate import (
        build_gate_report as build_research_evidence_gate_report,
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
    from source_to_intent_research_kernel_ingress_runtime_backend_alignment import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_CONTRACT,
        assert_kernel_ingress_runtime_backend_alignment_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_backend_alignment import (
        build_report as build_kernel_ingress_runtime_backend_alignment_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_coverage_policy import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT,
        assert_kernel_ingress_runtime_coverage_policy_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_coverage_policy import (
        build_report as build_kernel_ingress_runtime_coverage_policy_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_kernel_ingress_runtime_matrix_report,
    )
    from source_to_intent_research_proof_bundle import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_CONTRACT,
        assert_proof_bundle_report_contract,
    )
    from source_to_intent_research_proof_bundle import (
        build_report as build_research_proof_bundle_report,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
)

SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_capability_claim_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_CONTRACT = (
    "source_to_intent_research_capability_claim.review.v0"
)
SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_ID = (
    "bounded_universal_compute_research_slice"
)
SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_STATUS = (
    "supported_for_current_research_scope"
)
SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_ARTIFACT_POLICY = (
    "digest_only_source_free"
)
SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_BOUNDARY = (
    "static_research_sources_to_capability_selected_trusted_runtime"
)
SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_SCOPE = (
    "accepted_source_to_intent_kernel_ingress_mvp_pipeline"
)
SOURCE_TO_INTENT_RESEARCH_CAPABILITY_SUPPORTED_CLAIMS = (
    "bounded_source_to_intent_ingress",
    "mvp_operation_family_pipeline",
    "capability_selected_simulator_execution",
    "digest_bound_evidence_chain",
    "source_free_review_artifacts",
)
SOURCE_TO_INTENT_RESEARCH_CAPABILITY_BLOCKED_CLAIMS = (
    "arbitrary_backend_execution",
    "general_triton_source_ingestion",
    "hardware_certification",
    "native_performance_claim",
    "production_parser",
    "vendor_compiler_replacement",
)
SOURCE_TO_INTENT_RESEARCH_CAPABILITY_ACCEPTANCE_CHECKS = (
    "global_proof_bundle_passes",
    "global_evidence_gate_passes",
    "kernel_ingress_proof_bundle_passes",
    "kernel_ingress_evidence_gate_passes",
    "runtime_matrix_has_combined_mvp_pipeline",
    "runtime_coverage_policy_requires_exact_trace_counts",
    "runtime_backend_alignment_uses_trusted_executors",
)
SOURCE_TO_INTENT_RESEARCH_CAPABILITY_OPERATION_PATH = (
    "matmul",
    "softmax",
    "reduction",
    "elementwise",
)
SOURCE_TO_INTENT_RESEARCH_CAPABILITY_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"module_source":',
    "python_source",
    '"raw_source":',
    "raw_source_text",
    "raw_tensor_value",
    "secret.txt",
    "source_intent_payload",
    "tl.dot",
    "tl.store",
)

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "accepted_kernel_count",
        "accepted_operation_families",
        "artifact_policy",
        "blocked_claims",
        "claim_boundary",
        "claim_contract",
        "claim_id",
        "claim_scope",
        "claim_status",
        "combined_pipeline_kernel",
        "combined_pipeline_operation_path",
        "default_parser_status",
        "evidence",
        "evidence_count",
        "minimum_acceptance_checks",
        "parser_status",
        "runtime_case_count",
        "schema_version",
        "status",
        "supported_claims",
        "trusted_runtime_backends",
    }
)
_EVIDENCE_KEYS = frozenset(
    {"artifact_id", "artifact_kind", "contract", "digest", "status"}
)
_REQUIRED_EVIDENCE = (
    (
        "source_to_intent_research_proof_bundle",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_CONTRACT,
    ),
    (
        "source_to_intent_research_evidence_gate",
        "text_gate",
        SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE_CONTRACT,
    ),
    (
        "source_to_intent_research_kernel_ingress_proof_bundle",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CONTRACT,
    ),
    (
        "source_to_intent_research_kernel_ingress_evidence_gate",
        "text_gate",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_CONTRACT,
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_matrix",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_coverage_policy",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT,
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_backend_alignment",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_CONTRACT,
    ),
)


def build_research_capability_claim_report() -> dict[str, object]:
    """Return the source-free claim supported by current research evidence."""

    artifact_texts = {
        "source_to_intent_research_proof_bundle": (
            build_research_proof_bundle_report()
        ),
        "source_to_intent_research_evidence_gate": (
            build_research_evidence_gate_report()
        ),
        "source_to_intent_research_kernel_ingress_proof_bundle": (
            build_kernel_ingress_proof_bundle_report()
        ),
        "source_to_intent_research_kernel_ingress_evidence_gate": (
            build_kernel_ingress_evidence_gate_report()
        ),
        "source_to_intent_research_kernel_ingress_runtime_matrix": (
            build_kernel_ingress_runtime_matrix_report()
        ),
        "source_to_intent_research_kernel_ingress_runtime_coverage_policy": (
            build_kernel_ingress_runtime_coverage_policy_report()
        ),
        "source_to_intent_research_kernel_ingress_runtime_backend_alignment": (
            build_kernel_ingress_runtime_backend_alignment_report()
        ),
    }
    runtime_matrix = _assert_evidence_payloads(artifact_texts)
    runtime_backend_alignment = json.loads(
        artifact_texts[
            "source_to_intent_research_kernel_ingress_runtime_backend_alignment"
        ]
    )
    evidence = [
        {
            "artifact_id": artifact_id,
            "artifact_kind": artifact_kind,
            "contract": contract,
            "digest": _digest(artifact_texts[artifact_id]),
            "status": "accepted",
        }
        for artifact_id, artifact_kind, contract in _REQUIRED_EVIDENCE
    ]
    report: dict[str, object] = {
        "accepted_kernel_count": runtime_matrix["case_count"],
        "accepted_operation_families": list(
            runtime_matrix["covered_operation_families"]
        ),
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_ARTIFACT_POLICY,
        "blocked_claims": list(SOURCE_TO_INTENT_RESEARCH_CAPABILITY_BLOCKED_CLAIMS),
        "claim_boundary": SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_BOUNDARY,
        "claim_contract": SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_CONTRACT,
        "claim_id": SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_ID,
        "claim_scope": SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_SCOPE,
        "claim_status": SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_STATUS,
        "combined_pipeline_kernel": "mvp_pipeline",
        "combined_pipeline_operation_path": list(
            SOURCE_TO_INTENT_RESEARCH_CAPABILITY_OPERATION_PATH
        ),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "minimum_acceptance_checks": list(
            SOURCE_TO_INTENT_RESEARCH_CAPABILITY_ACCEPTANCE_CHECKS
        ),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "runtime_case_count": runtime_matrix["case_count"],
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_REPORT_SCHEMA_VERSION
        ),
        "status": "PASS",
        "supported_claims": list(SOURCE_TO_INTENT_RESEARCH_CAPABILITY_SUPPORTED_CLAIMS),
        "trusted_runtime_backends": list(
            runtime_backend_alignment["required_backend_names"]
        ),
    }
    assert_research_capability_claim_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the research capability claim."""

    return json.dumps(
        build_research_capability_claim_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_research_capability_claim_report_contract(report: object) -> None:
    """Fail closed unless the research capability claim matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError("source-to-intent research capability claim must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "accepted_kernel_count": 4,
        "accepted_operation_families": ["elementwise", "matmul", "reduction", "softmax"],
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_ARTIFACT_POLICY,
        "blocked_claims": list(SOURCE_TO_INTENT_RESEARCH_CAPABILITY_BLOCKED_CLAIMS),
        "claim_boundary": SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_BOUNDARY,
        "claim_contract": SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_CONTRACT,
        "claim_id": SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_ID,
        "claim_scope": SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_SCOPE,
        "claim_status": SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_STATUS,
        "combined_pipeline_kernel": "mvp_pipeline",
        "combined_pipeline_operation_path": list(
            SOURCE_TO_INTENT_RESEARCH_CAPABILITY_OPERATION_PATH
        ),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "evidence_count": len(_REQUIRED_EVIDENCE),
        "minimum_acceptance_checks": list(
            SOURCE_TO_INTENT_RESEARCH_CAPABILITY_ACCEPTANCE_CHECKS
        ),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "runtime_case_count": 4,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_REPORT_SCHEMA_VERSION
        ),
        "status": "PASS",
        "supported_claims": list(SOURCE_TO_INTENT_RESEARCH_CAPABILITY_SUPPORTED_CLAIMS),
        "trusted_runtime_backends": ["linear-sim", "vector-sim"],
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"source-to-intent research capability {key} drift")
    evidence = report["evidence"]
    if not isinstance(evidence, list) or len(evidence) != len(_REQUIRED_EVIDENCE):
        raise ValueError("source-to-intent research capability evidence drift")
    observed_ids = []
    for index, item in enumerate(evidence):
        observed_ids.append(_assert_evidence_contract(index, item))
    if tuple(observed_ids) != tuple(item[0] for item in _REQUIRED_EVIDENCE):
        raise ValueError("source-to-intent research capability evidence order drift")
    _assert_report_is_source_free(report)


def _assert_evidence_payloads(
    artifact_texts: Mapping[str, str],
) -> Mapping[str, object]:
    research_proof = json.loads(artifact_texts["source_to_intent_research_proof_bundle"])
    assert_proof_bundle_report_contract(research_proof)
    research_gate = artifact_texts["source_to_intent_research_evidence_gate"]
    _assert_research_evidence_gate_contract(research_gate)
    kernel_proof = json.loads(
        artifact_texts["source_to_intent_research_kernel_ingress_proof_bundle"]
    )
    assert_kernel_ingress_proof_bundle_report_contract(kernel_proof)
    kernel_gate = artifact_texts["source_to_intent_research_kernel_ingress_evidence_gate"]
    assert_kernel_ingress_evidence_gate_report_contract(kernel_gate)
    runtime_matrix = json.loads(
        artifact_texts["source_to_intent_research_kernel_ingress_runtime_matrix"]
    )
    assert_kernel_ingress_runtime_matrix_report_contract(runtime_matrix)
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
    _assert_mvp_pipeline_bound(runtime_matrix, runtime_coverage_policy)
    for text in artifact_texts.values():
        _assert_text_is_source_free(text)
    return runtime_matrix


def _assert_mvp_pipeline_bound(
    runtime_matrix: Mapping[str, object],
    runtime_coverage_policy: Mapping[str, object],
) -> None:
    cases = runtime_matrix["cases"]
    if not isinstance(cases, list):
        raise ValueError("source-to-intent research capability runtime cases drift")
    mvp_cases = [
        case
        for case in cases
        if isinstance(case, Mapping)
        and case.get("case_id") == "research_module_mvp_pipeline"
    ]
    if len(mvp_cases) != 1:
        raise ValueError("source-to-intent research capability mvp case drift")
    mvp_case = mvp_cases[0]
    expected_mvp_values = {
        "backend_sequence": ["linear-sim", "vector-sim", "vector-sim", "vector-sim"],
        "kernel_name": "mvp_pipeline",
        "operation_families": ["elementwise", "matmul", "reduction", "softmax"],
        "terminal_outputs": ["stable"],
        "trace_step_count": 4,
    }
    for key, expected in expected_mvp_values.items():
        if mvp_case.get(key) != expected:
            raise ValueError(
                f"source-to-intent research capability mvp {key} drift"
            )
    trace_counts = runtime_coverage_policy["required_trace_step_count_per_case"]
    if not isinstance(trace_counts, Mapping):
        raise ValueError("source-to-intent research capability trace policy drift")
    if trace_counts.get("research_module_mvp_pipeline") != 4:
        raise ValueError("source-to-intent research capability mvp trace drift")


def _assert_research_evidence_gate_contract(text: str) -> None:
    required_fragments = (
        "source_to_intent.research_evidence_gate",
        f'gate_contract = "{SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE_CONTRACT}"',
        'kernel_ingress_evidence_gate = "passed"',
        'kernel_ingress_proof_bundle = "passed"',
        'kernel_ingress = "passed"',
        'source_runtime_smoke = "passed"',
        'status = "PASS"',
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise ValueError("source-to-intent research capability gate drift")
    _assert_text_is_source_free(text)


def _assert_evidence_contract(index: int, item: object) -> str:
    if not isinstance(item, Mapping):
        raise ValueError("source-to-intent research capability evidence must be object")
    _assert_exact_keys("evidence", item, _EVIDENCE_KEYS)
    expected_id, expected_kind, expected_contract = _REQUIRED_EVIDENCE[index]
    expected_values = {
        "artifact_id": expected_id,
        "artifact_kind": expected_kind,
        "contract": expected_contract,
        "status": "accepted",
    }
    for key, expected in expected_values.items():
        if item[key] != expected:
            raise ValueError(f"source-to-intent research capability {key} drift")
    digest = item["digest"]
    if not isinstance(digest, str) or not _SHA256_DIGEST_PATTERN.fullmatch(digest):
        raise ValueError("source-to-intent research capability digest drift")
    return expected_id


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"source-to-intent research capability {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(
            "source-to-intent research capability report is not JSON data"
        ) from exc
    _assert_text_is_source_free(text)


def _assert_text_is_source_free(text: str) -> None:
    for fragment in SOURCE_TO_INTENT_RESEARCH_CAPABILITY_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise ValueError(
                "source-to-intent research capability contains forbidden material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
