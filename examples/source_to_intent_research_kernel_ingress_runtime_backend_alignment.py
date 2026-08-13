"""Bind Kernel Ingress runtime backends to trusted executor conformance."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

from tuc.report_output import emit_public_json_report

try:
    from examples.runtime_executor_conformance import (
        build_report as build_runtime_executor_conformance_report,
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
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_executor_conformance import (  # type: ignore[no-redef]
        build_report as build_runtime_executor_conformance_report,
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

from tuc.runtime import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT,
    RUNTIME_EXECUTOR_CONFORMANCE_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_runtime_backend_alignment_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_CONTRACT = (
    "source_to_intent_research_kernel_ingress_runtime_backend_alignment.trusted_executor.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_ARTIFACT_POLICY = (
    "metadata_only_source_free"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_SOURCE_BOUNDARY = (
    "kernel_ingress_runtime_matrix_to_trusted_executor_conformance"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_FORBIDDEN_FRAGMENTS = (
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
        "alignment_contract",
        "artifact_policy",
        "backend_support_matrix",
        "blocked_execution_surfaces",
        "case_alignments",
        "observed_backend_names",
        "required_backend_names",
        "runtime_coverage_policy_contract",
        "runtime_coverage_policy_digest",
        "runtime_executor_conformance_contract",
        "runtime_executor_conformance_digest",
        "runtime_executor_conformance_schema_version",
        "runtime_executor_contract",
        "runtime_matrix_contract",
        "runtime_matrix_digest",
        "schema_version",
        "source_boundary",
        "status",
        "trusted_executor_registry",
    }
)
_BACKEND_SUPPORT_KEYS = frozenset(
    {"backend_name", "status", "supported_operation_families"}
)
_CASE_ALIGNMENT_KEYS = frozenset(
    {
        "backend_sequence",
        "case_id",
        "kernel_name",
        "operation_families",
        "status",
        "supported_operation_families",
    }
)
_REQUIRED_BACKEND_NAMES = ("linear-sim", "vector-sim")
_EXPECTED_BACKEND_SUPPORT = {
    "linear-sim": ["matmul", "reduction"],
    "vector-sim": ["elementwise", "reduction", "softmax"],
}
_EXPECTED_CASE_ALIGNMENTS = (
    {
        "backend_sequence": ["linear-sim", "vector-sim"],
        "case_id": "research_module_matmul_elementwise",
        "kernel_name": "matmul_elementwise",
        "operation_families": ["elementwise", "matmul"],
        "status": "aligned",
        "supported_operation_families": ["elementwise", "matmul", "reduction", "softmax"],
    },
    {
        "backend_sequence": ["vector-sim", "vector-sim"],
        "case_id": "research_module_softmax_reduction",
        "kernel_name": "softmax_reduction",
        "operation_families": ["reduction", "softmax"],
        "status": "aligned",
        "supported_operation_families": ["elementwise", "reduction", "softmax"],
    },
    {
        "backend_sequence": ["linear-sim", "vector-sim"],
        "case_id": "research_module_matmul_reduction",
        "kernel_name": "matmul_reduction",
        "operation_families": ["matmul", "reduction"],
        "status": "aligned",
        "supported_operation_families": ["elementwise", "matmul", "reduction", "softmax"],
    },
    {
        "backend_sequence": ["vector-sim", "vector-sim"],
        "case_id": "research_module_softmax_elementwise",
        "kernel_name": "softmax_elementwise",
        "operation_families": ["elementwise", "softmax"],
        "status": "aligned",
        "supported_operation_families": ["elementwise", "reduction", "softmax"],
    },
    {
        "backend_sequence": ["linear-sim", "vector-sim", "vector-sim", "vector-sim"],
        "case_id": "research_module_mvp_pipeline",
        "kernel_name": "mvp_pipeline",
        "operation_families": ["elementwise", "matmul", "reduction", "softmax"],
        "status": "aligned",
        "supported_operation_families": ["elementwise", "matmul", "reduction", "softmax"],
    },
)


def build_kernel_ingress_runtime_backend_alignment_report() -> dict[str, object]:
    """Return source-free alignment between Kernel Ingress and trusted executors."""

    runtime_matrix_text = build_kernel_ingress_runtime_matrix_report()
    runtime_coverage_policy_text = build_kernel_ingress_runtime_coverage_policy_report()
    conformance_text = build_runtime_executor_conformance_report()
    runtime_matrix = json.loads(runtime_matrix_text)
    runtime_coverage_policy = json.loads(runtime_coverage_policy_text)
    conformance = json.loads(conformance_text)
    assert_kernel_ingress_runtime_matrix_report_contract(runtime_matrix)
    assert_kernel_ingress_runtime_coverage_policy_report_contract(
        runtime_coverage_policy
    )
    _assert_runtime_executor_conformance_payload(conformance)
    backend_support = _backend_support_matrix(conformance)
    case_alignments = _case_alignments(runtime_matrix, backend_support)
    report: dict[str, object] = {
        "alignment_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_CONTRACT
        ),
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_ARTIFACT_POLICY
        ),
        "backend_support_matrix": backend_support,
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "case_alignments": case_alignments,
        "observed_backend_names": _observed_backend_names(runtime_matrix),
        "required_backend_names": list(_REQUIRED_BACKEND_NAMES),
        "runtime_coverage_policy_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT
        ),
        "runtime_coverage_policy_digest": _digest(runtime_coverage_policy_text),
        "runtime_executor_conformance_contract": RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT,
        "runtime_executor_conformance_digest": _digest(conformance_text),
        "runtime_executor_conformance_schema_version": (
            RUNTIME_EXECUTOR_CONFORMANCE_REPORT_SCHEMA_VERSION
        ),
        "runtime_executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "runtime_matrix_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
        ),
        "runtime_matrix_digest": _digest(runtime_matrix_text),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    assert_kernel_ingress_runtime_backend_alignment_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for runtime backend alignment."""

    return json.dumps(
        build_kernel_ingress_runtime_backend_alignment_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    emit_public_json_report(build_report())


def assert_kernel_ingress_runtime_backend_alignment_report_contract(
    report: object,
) -> None:
    """Fail closed unless the runtime backend alignment report matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress runtime backend alignment report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    runtime_matrix_text = build_kernel_ingress_runtime_matrix_report()
    runtime_coverage_policy_text = build_kernel_ingress_runtime_coverage_policy_report()
    conformance_text = build_runtime_executor_conformance_report()
    expected_values = {
        "alignment_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_CONTRACT
        ),
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_ARTIFACT_POLICY
        ),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "observed_backend_names": list(_REQUIRED_BACKEND_NAMES),
        "required_backend_names": list(_REQUIRED_BACKEND_NAMES),
        "runtime_coverage_policy_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT
        ),
        "runtime_coverage_policy_digest": _digest(runtime_coverage_policy_text),
        "runtime_executor_conformance_contract": RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT,
        "runtime_executor_conformance_digest": _digest(conformance_text),
        "runtime_executor_conformance_schema_version": (
            RUNTIME_EXECUTOR_CONFORMANCE_REPORT_SCHEMA_VERSION
        ),
        "runtime_executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "runtime_matrix_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
        ),
        "runtime_matrix_digest": _digest(runtime_matrix_text),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"kernel ingress runtime backend alignment {key} drift")
    _assert_backend_support_matrix(report["backend_support_matrix"])
    _assert_case_alignments(report["case_alignments"])
    for digest_key in (
        "runtime_matrix_digest",
        "runtime_coverage_policy_digest",
        "runtime_executor_conformance_digest",
    ):
        value = report[digest_key]
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError("kernel ingress runtime backend alignment digest drift")
    _assert_report_is_source_free(report)


def _assert_runtime_executor_conformance_payload(report: Mapping[object, object]) -> None:
    expected_values = {
        "conformance_contract": RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "issues": [],
        "passed": True,
        "schema_version": RUNTIME_EXECUTOR_CONFORMANCE_REPORT_SCHEMA_VERSION,
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    for key, expected in expected_values.items():
        if report.get(key) != expected:
            raise ValueError(f"kernel ingress runtime backend alignment {key} drift")
    checked_cases = report.get("checked_cases")
    if not isinstance(checked_cases, list):
        raise ValueError("kernel ingress runtime backend alignment conformance drift")


def _backend_support_matrix(
    conformance: Mapping[object, object],
) -> list[dict[str, object]]:
    checked_cases = conformance["checked_cases"]
    if not isinstance(checked_cases, list):
        raise ValueError("kernel ingress runtime backend alignment conformance drift")
    observed: dict[str, list[str]] = {backend: [] for backend in _REQUIRED_BACKEND_NAMES}
    for case in checked_cases:
        if not isinstance(case, Mapping):
            raise ValueError("kernel ingress runtime backend alignment case drift")
        backend_name = case["executor_name"]
        if backend_name not in observed:
            continue
        if case["expected_status"] == "supported" and case["observed_status"] == (
            "executed"
        ):
            observed[str(backend_name)].append(str(case["operation_kind"]))
    matrix = [
        {
            "backend_name": backend_name,
            "status": "trusted_conformant",
            "supported_operation_families": sorted(set(observed[backend_name])),
        }
        for backend_name in _REQUIRED_BACKEND_NAMES
    ]
    _assert_backend_support_matrix(matrix)
    return matrix


def _case_alignments(
    runtime_matrix: Mapping[object, object],
    backend_support: list[dict[str, object]],
) -> list[dict[str, object]]:
    support_by_backend = {
        str(row["backend_name"]): set(_string_list(row["supported_operation_families"]))
        for row in backend_support
    }
    cases = runtime_matrix["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress runtime backend alignment matrix case drift")
    alignments: list[dict[str, object]] = []
    for case in cases:
        if not isinstance(case, Mapping):
            raise ValueError("kernel ingress runtime backend alignment matrix case drift")
        backend_sequence = _string_list(case["backend_sequence"])
        supported = sorted(
            {
                operation
                for backend in backend_sequence
                for operation in support_by_backend.get(backend, set())
            }
        )
        operation_families = _string_list(case["operation_families"])
        if not set(operation_families).issubset(set(supported)):
            raise ValueError("kernel ingress runtime backend alignment support drift")
        alignments.append(
            {
                "backend_sequence": backend_sequence,
                "case_id": str(case["case_id"]),
                "kernel_name": str(case["kernel_name"]),
                "operation_families": operation_families,
                "status": "aligned",
                "supported_operation_families": supported,
            }
        )
    _assert_case_alignments(alignments)
    return alignments


def _observed_backend_names(runtime_matrix: Mapping[object, object]) -> list[str]:
    cases = runtime_matrix["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress runtime backend alignment matrix case drift")
    observed = []
    for case in cases:
        if not isinstance(case, Mapping):
            raise ValueError("kernel ingress runtime backend alignment matrix case drift")
        for backend_name in _string_list(case["backend_sequence"]):
            if backend_name not in observed:
                observed.append(backend_name)
    return observed


def _assert_backend_support_matrix(value: object) -> None:
    if not isinstance(value, list):
        raise ValueError("kernel ingress runtime backend alignment support matrix drift")
    if len(value) != len(_REQUIRED_BACKEND_NAMES):
        raise ValueError("kernel ingress runtime backend alignment support count drift")
    for row, backend_name in zip(value, _REQUIRED_BACKEND_NAMES, strict=True):
        if not isinstance(row, Mapping):
            raise ValueError("kernel ingress runtime backend alignment support row drift")
        _assert_exact_keys("backend support", row, _BACKEND_SUPPORT_KEYS)
        if row["backend_name"] != backend_name:
            raise ValueError("kernel ingress runtime backend alignment backend name drift")
        if row["status"] != "trusted_conformant":
            raise ValueError("kernel ingress runtime backend alignment status drift")
        if row["supported_operation_families"] != _EXPECTED_BACKEND_SUPPORT[backend_name]:
            raise ValueError("kernel ingress runtime backend alignment support drift")


def _assert_case_alignments(value: object) -> None:
    if not isinstance(value, list):
        raise ValueError("kernel ingress runtime backend alignment cases drift")
    if len(value) != len(_EXPECTED_CASE_ALIGNMENTS):
        raise ValueError("kernel ingress runtime backend alignment case count drift")
    for row, expected in zip(value, _EXPECTED_CASE_ALIGNMENTS, strict=True):
        if not isinstance(row, Mapping):
            raise ValueError("kernel ingress runtime backend alignment case row drift")
        _assert_exact_keys("case alignment", row, _CASE_ALIGNMENT_KEYS)
        for key, expected_value in expected.items():
            if row[key] != expected_value:
                raise ValueError(f"kernel ingress runtime backend alignment {key} drift")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("kernel ingress runtime backend alignment list drift")
    return [str(item) for item in value]


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"kernel ingress runtime backend alignment {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(
            "kernel ingress runtime backend alignment report is not JSON data"
        ) from exc
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress runtime backend alignment contains forbidden "
                "source or value material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
