"""Emit the canonical metadata-only Proof of Backend Equivalence."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

from examples.runtime_mixed_backend_equivalence import (
    build_mixed_backend_equivalence_report,
)
from tuc import (
    RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    RUNTIME_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    dump_runtime_backend_equivalence_report,
    runtime_backend_equivalence_report_to_dict,
)
from tuc.report_output import emit_public_json_report

PROOF_OF_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION = (
    "tuc.proof_of_backend_equivalence_report.v0"
)
PROOF_OF_BACKEND_EQUIVALENCE_CONTRACT = "proof_of_backend_equivalence.mixed_backend.v0"
PROOF_OF_BACKEND_EQUIVALENCE_ARTIFACT_STATUS = "review_evidence"
PROOF_OF_BACKEND_EQUIVALENCE_CLAIM = (
    "same_compute_intent_preserves_terminal_semantics_across_mixed_backend_placement"
)
PROOF_OF_BACKEND_EQUIVALENCE_PROOF_KIND = "backend_equivalence"
PROOF_OF_BACKEND_EQUIVALENCE_STATUS = "PASS"
PROOF_OF_BACKEND_EQUIVALENCE_BASELINE_PLACEMENT = "reference_cpu"
PROOF_OF_BACKEND_EQUIVALENCE_CANDIDATE_PLACEMENT = "systolic_sim_plus_vector_sim"
PROOF_OF_BACKEND_EQUIVALENCE_SOURCE_REPORT_ID = "runtime_mixed_backend_equivalence"
PROOF_OF_BACKEND_EQUIVALENCE_NON_CLAIMS = (
    "native_device_execution",
    "native_performance_parity",
    "physical_device_residency",
    "backend_plugin_safety",
    "broad_source_parser_correctness",
)
PROOF_OF_BACKEND_EQUIVALENCE_FORBIDDEN_FRAGMENTS = (
    "backend_artifact",
    "command",
    "device_id",
    "env",
    "generated_code",
    "host_path",
    "plugin_entrypoint",
    "python_source",
    "raw_benchmark_output",
    "raw_tensor_value",
    "raw_timing_samples",
    "runtime_handle",
    "tensor_value",
)

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_status",
        "baseline_backend_sequence",
        "baseline_placement",
        "baseline_run_id",
        "blocked_execution_surfaces",
        "candidate_backend_sequence",
        "candidate_placement",
        "candidate_run_id",
        "claim",
        "comparison_count",
        "executor_contract",
        "graph_name",
        "non_claims",
        "proof_contract",
        "proof_kind",
        "proof_status",
        "raw_value_policy",
        "runtime_equivalence_comparison_digest",
        "runtime_equivalence_contract",
        "runtime_equivalence_report_digest",
        "runtime_equivalence_schema_version",
        "schema_version",
        "source_report_id",
        "terminal_output_checks",
        "trusted_executor_registry",
    }
)
_CHECK_KEYS = frozenset(
    {
        "atol",
        "baseline_dtype",
        "baseline_output_value_status",
        "baseline_shape",
        "candidate_dtype",
        "candidate_output_value_status",
        "candidate_shape",
        "comparison_status",
        "expected_dtype",
        "expected_shape",
        "rtol",
        "tensor_name",
    }
)


def build_proof_of_backend_equivalence_report() -> dict[str, object]:
    """Return the canonical mixed-backend equivalence proof summary."""

    equivalence = build_mixed_backend_equivalence_report()
    equivalence_text = dump_runtime_backend_equivalence_report(equivalence)
    equivalence_payload = runtime_backend_equivalence_report_to_dict(equivalence)
    _assert_source_equivalence_payload(equivalence_payload)
    baseline_run, candidate_run = equivalence_payload["runs"]
    if not isinstance(baseline_run, dict) or not isinstance(candidate_run, dict):
        raise ValueError("proof of backend equivalence run shape drift")
    report: dict[str, object] = {
        "artifact_status": PROOF_OF_BACKEND_EQUIVALENCE_ARTIFACT_STATUS,
        "baseline_backend_sequence": baseline_run["planned_backend_sequence"],
        "baseline_placement": PROOF_OF_BACKEND_EQUIVALENCE_BASELINE_PLACEMENT,
        "baseline_run_id": equivalence_payload["baseline_run_id"],
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "candidate_backend_sequence": candidate_run["planned_backend_sequence"],
        "candidate_placement": PROOF_OF_BACKEND_EQUIVALENCE_CANDIDATE_PLACEMENT,
        "candidate_run_id": equivalence_payload["candidate_run_id"],
        "claim": PROOF_OF_BACKEND_EQUIVALENCE_CLAIM,
        "comparison_count": equivalence_payload["comparison_count"],
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "graph_name": equivalence_payload["graph_name"],
        "non_claims": list(PROOF_OF_BACKEND_EQUIVALENCE_NON_CLAIMS),
        "proof_contract": PROOF_OF_BACKEND_EQUIVALENCE_CONTRACT,
        "proof_kind": PROOF_OF_BACKEND_EQUIVALENCE_PROOF_KIND,
        "proof_status": PROOF_OF_BACKEND_EQUIVALENCE_STATUS,
        "raw_value_policy": RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
        "runtime_equivalence_comparison_digest": equivalence_payload[
            "comparison_metadata_digest"
        ],
        "runtime_equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "runtime_equivalence_report_digest": _digest(equivalence_text),
        "runtime_equivalence_schema_version": (
            RUNTIME_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION
        ),
        "schema_version": PROOF_OF_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION,
        "source_report_id": PROOF_OF_BACKEND_EQUIVALENCE_SOURCE_REPORT_ID,
        "terminal_output_checks": _terminal_output_checks(equivalence_payload),
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    assert_proof_of_backend_equivalence_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the canonical backend-equivalence proof."""

    return json.dumps(
        build_proof_of_backend_equivalence_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    emit_public_json_report(build_report())


def assert_proof_of_backend_equivalence_report_contract(report: object) -> None:
    """Fail closed unless the proof report matches the accepted contract."""

    if not isinstance(report, Mapping):
        raise ValueError("proof of backend equivalence report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected = {
        "artifact_status": PROOF_OF_BACKEND_EQUIVALENCE_ARTIFACT_STATUS,
        "baseline_backend_sequence": [
            "reference-cpu",
            "reference-cpu",
            "reference-cpu",
            "reference-cpu",
        ],
        "baseline_placement": PROOF_OF_BACKEND_EQUIVALENCE_BASELINE_PLACEMENT,
        "baseline_run_id": "reference_cpu",
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "candidate_backend_sequence": [
            "systolic-sim",
            "vector-sim",
            "vector-sim",
            "vector-sim",
        ],
        "candidate_placement": PROOF_OF_BACKEND_EQUIVALENCE_CANDIDATE_PLACEMENT,
        "candidate_run_id": "mixed_accelerators",
        "claim": PROOF_OF_BACKEND_EQUIVALENCE_CLAIM,
        "comparison_count": 1,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "graph_name": "runtime_mixed_backend_equivalence",
        "non_claims": list(PROOF_OF_BACKEND_EQUIVALENCE_NON_CLAIMS),
        "proof_contract": PROOF_OF_BACKEND_EQUIVALENCE_CONTRACT,
        "proof_kind": PROOF_OF_BACKEND_EQUIVALENCE_PROOF_KIND,
        "proof_status": PROOF_OF_BACKEND_EQUIVALENCE_STATUS,
        "raw_value_policy": RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
        "runtime_equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "runtime_equivalence_schema_version": (
            RUNTIME_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION
        ),
        "schema_version": PROOF_OF_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION,
        "source_report_id": PROOF_OF_BACKEND_EQUIVALENCE_SOURCE_REPORT_ID,
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    for key, expected_value in expected.items():
        if report[key] != expected_value:
            raise ValueError(f"proof of backend equivalence {key} drift")
    for digest_key in (
        "runtime_equivalence_comparison_digest",
        "runtime_equivalence_report_digest",
    ):
        digest = report[digest_key]
        if not isinstance(digest, str) or not _SHA256_DIGEST_PATTERN.fullmatch(digest):
            raise ValueError(f"proof of backend equivalence {digest_key} drift")
    checks = report["terminal_output_checks"]
    if not isinstance(checks, list) or len(checks) != 1:
        raise ValueError("proof of backend equivalence output check drift")
    _assert_output_check(checks[0])
    _assert_report_is_metadata_only(report)


def _assert_source_equivalence_payload(payload: Mapping[str, object]) -> None:
    expected = {
        "baseline_run_id": "reference_cpu",
        "candidate_run_id": "mixed_accelerators",
        "comparison_count": 1,
        "equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "graph_name": "runtime_mixed_backend_equivalence",
        "issues": [],
        "passed": True,
        "raw_value_policy": RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
        "run_count": 2,
        "schema_version": RUNTIME_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION,
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    for key, expected_value in expected.items():
        if payload[key] != expected_value:
            raise ValueError(f"source backend equivalence {key} drift")


def _terminal_output_checks(payload: Mapping[str, object]) -> list[dict[str, object]]:
    comparisons = payload["comparisons"]
    if not isinstance(comparisons, list) or len(comparisons) != 1:
        raise ValueError("proof of backend equivalence comparison drift")
    checks = []
    for comparison in comparisons:
        if not isinstance(comparison, Mapping):
            raise ValueError("proof of backend equivalence comparison shape drift")
        checks.append(
            {
                "atol": comparison["atol"],
                "baseline_dtype": comparison["baseline_dtype"],
                "baseline_output_value_status": comparison[
                    "baseline_output_value_status"
                ],
                "baseline_shape": comparison["baseline_shape"],
                "candidate_dtype": comparison["candidate_dtype"],
                "candidate_output_value_status": comparison[
                    "candidate_output_value_status"
                ],
                "candidate_shape": comparison["candidate_shape"],
                "comparison_status": comparison["comparison_status"],
                "expected_dtype": comparison["expected_dtype"],
                "expected_shape": comparison["expected_shape"],
                "rtol": comparison["rtol"],
                "tensor_name": comparison["tensor_name"],
            }
        )
    return checks


def _assert_output_check(check: object) -> None:
    if not isinstance(check, Mapping):
        raise ValueError("proof of backend equivalence output check must be object")
    _assert_exact_keys("output check", check, _CHECK_KEYS)
    expected = {
        "atol": 1e-12,
        "baseline_dtype": "float64",
        "baseline_output_value_status": RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
        "baseline_shape": [2],
        "candidate_dtype": "float64",
        "candidate_output_value_status": RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
        "candidate_shape": [2],
        "comparison_status": "matched",
        "expected_dtype": "float64",
        "expected_shape": [2],
        "rtol": 1e-12,
        "tensor_name": "activated",
    }
    for key, expected_value in expected.items():
        if check[key] != expected_value:
            raise ValueError(f"proof of backend equivalence output {key} drift")


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"proof of backend equivalence {context} drift")


def _assert_report_is_metadata_only(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError("proof of backend equivalence report is not JSON") from exc
    for fragment in PROOF_OF_BACKEND_EQUIVALENCE_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise ValueError(
                "proof of backend equivalence contains forbidden executable "
                "or value material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
