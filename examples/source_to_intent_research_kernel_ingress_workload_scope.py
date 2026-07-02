"""Bind Kernel Ingress shape-profile evidence to workload-scope review data."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles import (  # noqa: E501
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT,
        assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles import (  # noqa: E501
        build_report as build_kernel_ingress_shape_profile_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles import (  # type: ignore[no-redef] # noqa: E501
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT,
        assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract,
    )
    from source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles import (  # noqa: E501
        build_report as build_kernel_ingress_shape_profile_report,
    )

from tuc import (
    WORKLOAD_SCOPE_ARTIFACT_STATUS,
    WORKLOAD_SCOPE_CLAIM_STATUS,
    WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION,
    WorkloadScope,
    build_workload_scope_report,
    dump_workload_scope_report,
    workload_scope_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_workload_scope_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_CONTRACT = (
    "source_to_intent_research_kernel_ingress_workload_scope.performance_boundary.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_ARTIFACT_POLICY = (
    "metadata_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_SOURCE_BOUNDARY = (
    "kernel_ingress_shape_profile_evidence_to_workload_scope_review"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_PROPOSAL_NAME = (
    "kernel_ingress_shape_profile_workload_scope"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_CLAIM = (
    "shape_profile_evidence_bounds_future_performance_workload_scope"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_BLOCKED_CLAIMS = (
    "native_performance_claim",
    "native_performance_parity",
    "dynamic_shape_performance_claim",
    "planner_benefit_claim",
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_DTYPE_POLICY_ID = (
    "float64_reference"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_CORRECTNESS_REFERENCE_ID = (
    "kernel_ingress_reference_correctness"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"module_source":',
    "python_source",
    '"raw_source":',
    "raw_tensor_value",
    "secret.txt",
    "source_intent_payload",
    "tensor_value",
    "tl.dot",
    "tl.store",
)

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_policy",
        "binding_contract",
        "blocked_claims",
        "claim",
        "claim_boundary",
        "case_count",
        "issues",
        "native_performance_claim",
        "operation_families",
        "performance_claim_status",
        "profile_count",
        "profile_ids",
        "schema_version",
        "scope_count",
        "scopes",
        "source_boundary",
        "source_evidence_contract",
        "source_evidence_digest",
        "source_schema_version",
        "status",
        "trusted_runtime_backends",
        "workload_scope_artifact_status",
        "workload_scope_digest",
        "workload_scope_ready",
        "workload_scope_schema_version",
    }
)
_SCOPE_KEYS = frozenset(
    {
        "correctness_reference_id",
        "dtype_policy_id",
        "operation_family",
        "problem_size_max",
        "problem_size_min",
        "scope_id",
        "shape_profile_id",
    }
)
_OPERATION_FAMILY_ORDER = ("elementwise", "matmul", "reduction", "softmax")
_EXPECTED_PROFILE_IDS = ("base", "alternate")
_EXPECTED_SCOPE_COUNT = 24


def build_kernel_ingress_workload_scope_report() -> dict[str, object]:
    """Return a source-free workload-scope binding for Kernel Ingress evidence."""

    source_text = build_kernel_ingress_shape_profile_report()
    source_report = json.loads(source_text)
    assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract(
        source_report
    )
    workload_scope = build_workload_scope_report(
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_PROPOSAL_NAME,
        scopes=_workload_scopes_from_shape_profiles(source_report),
    )
    workload_scope_text = dump_workload_scope_report(workload_scope)
    workload_scope_payload = workload_scope_report_to_dict(workload_scope)
    report: dict[str, object] = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_ARTIFACT_POLICY
        ),
        "binding_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_CONTRACT
        ),
        "blocked_claims": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_BLOCKED_CLAIMS
        ),
        "claim": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_CLAIM,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "case_count": int(source_report["case_count"]),
        "issues": list(workload_scope_payload["issues"]),
        "native_performance_claim": False,
        "operation_families": list(_OPERATION_FAMILY_ORDER),
        "performance_claim_status": WORKLOAD_SCOPE_CLAIM_STATUS,
        "profile_count": int(source_report["profile_count"]),
        "profile_ids": list(source_report["profile_ids"]),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION
        ),
        "scope_count": len(workload_scope.scopes),
        "scopes": list(workload_scope_payload["scopes"]),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_SOURCE_BOUNDARY
        ),
        "source_evidence_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT
        ),
        "source_evidence_digest": _digest(source_text),
        "source_schema_version": str(source_report["schema_version"]),
        "status": "PASS",
        "trusted_runtime_backends": list(source_report["trusted_runtime_backends"]),
        "workload_scope_artifact_status": WORKLOAD_SCOPE_ARTIFACT_STATUS,
        "workload_scope_digest": _digest(workload_scope_text),
        "workload_scope_ready": bool(workload_scope_payload["workload_scope_ready"]),
        "workload_scope_schema_version": WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION,
    }
    assert_kernel_ingress_workload_scope_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for Kernel Ingress workload scope."""

    return json.dumps(
        build_kernel_ingress_workload_scope_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_kernel_ingress_workload_scope_report_contract(report: object) -> None:
    """Fail closed unless Kernel Ingress workload scope matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress workload scope report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    source_text = build_kernel_ingress_shape_profile_report()
    source_report = json.loads(source_text)
    assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract(
        source_report
    )
    workload_scope = build_workload_scope_report(
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_PROPOSAL_NAME,
        scopes=_workload_scopes_from_shape_profiles(source_report),
    )
    workload_scope_text = dump_workload_scope_report(workload_scope)
    expected_values = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_ARTIFACT_POLICY
        ),
        "binding_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_CONTRACT
        ),
        "blocked_claims": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_BLOCKED_CLAIMS
        ),
        "claim": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_CLAIM,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "case_count": 10,
        "issues": ["native_performance_claim_blocked"],
        "native_performance_claim": False,
        "operation_families": list(_OPERATION_FAMILY_ORDER),
        "performance_claim_status": WORKLOAD_SCOPE_CLAIM_STATUS,
        "profile_count": len(_EXPECTED_PROFILE_IDS),
        "profile_ids": list(_EXPECTED_PROFILE_IDS),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION
        ),
        "scope_count": _EXPECTED_SCOPE_COUNT,
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_SOURCE_BOUNDARY
        ),
        "source_evidence_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT
        ),
        "source_evidence_digest": _digest(source_text),
        "source_schema_version": str(source_report["schema_version"]),
        "status": "PASS",
        "trusted_runtime_backends": [
            "linear-sim",
            "reference-cpu",
            "vector-sim",
        ],
        "workload_scope_artifact_status": WORKLOAD_SCOPE_ARTIFACT_STATUS,
        "workload_scope_digest": _digest(workload_scope_text),
        "workload_scope_ready": True,
        "workload_scope_schema_version": WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION,
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"kernel ingress workload scope {key} drift")
    scopes = report["scopes"]
    if not isinstance(scopes, list) or len(scopes) != _EXPECTED_SCOPE_COUNT:
        raise ValueError("kernel ingress workload scope scope count drift")
    expected_scopes = workload_scope_report_to_dict(workload_scope)["scopes"]
    if scopes != expected_scopes:
        raise ValueError("kernel ingress workload scope scopes drift")
    for scope in scopes:
        _assert_scope_contract(scope)
    _assert_report_is_source_free(report)


def _workload_scopes_from_shape_profiles(
    source_report: Mapping[str, object],
) -> tuple[WorkloadScope, ...]:
    cases = source_report["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress workload scope source cases drift")
    scopes: list[WorkloadScope] = []
    for case in cases:
        if not isinstance(case, Mapping):
            raise ValueError("kernel ingress workload scope source case drift")
        case_id = str(case["case_id"])
        profile_id = str(case["profile_id"])
        shape_profile_id = f"kernel_ingress_{_short_case_id(case_id)}_{profile_id}"
        operation_families = case["operation_families"]
        if not isinstance(operation_families, list):
            raise ValueError("kernel ingress workload scope operation families drift")
        declared_shapes = case["declared_tensor_shapes"]
        if not isinstance(declared_shapes, Mapping):
            raise ValueError("kernel ingress workload scope declared shapes drift")
        for operation_family in operation_families:
            family = str(operation_family)
            scopes.append(
                WorkloadScope(
                    scope_id=f"{shape_profile_id}_{family}",
                    operation_family=family,
                    shape_profile_id=shape_profile_id,
                    dtype_policy_id=(
                        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_DTYPE_POLICY_ID
                    ),
                    problem_size_min=_problem_size_for(family, declared_shapes),
                    problem_size_max=_problem_size_for(family, declared_shapes),
                    correctness_reference_id=(
                        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_CORRECTNESS_REFERENCE_ID
                    ),
                )
            )
    return tuple(scopes)


def _problem_size_for(family: str, shapes: Mapping[str, object]) -> int:
    if family == "matmul":
        a_shape = _shape(shapes, "a")
        b_shape = _shape(shapes, "b")
        if len(a_shape) != 2 or len(b_shape) != 2 or a_shape[1] != b_shape[0]:
            raise ValueError("kernel ingress workload scope matmul shape drift")
        return a_shape[0] * a_shape[1] * b_shape[1]
    if family == "elementwise":
        return _product(_shape(shapes, "y"))
    if family in {"reduction", "softmax"}:
        if "x" in shapes:
            return _product(_shape(shapes, "x"))
        a_shape = _shape(shapes, "a")
        b_shape = _shape(shapes, "b")
        if len(a_shape) != 2 or len(b_shape) != 2 or a_shape[1] != b_shape[0]:
            raise ValueError("kernel ingress workload scope projection shape drift")
        return a_shape[0] * b_shape[1]
    raise ValueError("kernel ingress workload scope unsupported operation family")


def _shape(shapes: Mapping[str, object], name: str) -> tuple[int, ...]:
    value = shapes[name]
    if not isinstance(value, list):
        raise ValueError("kernel ingress workload scope shape drift")
    shape = tuple(int(dimension) for dimension in value)
    if not shape or any(dimension <= 0 for dimension in shape):
        raise ValueError("kernel ingress workload scope invalid shape")
    return shape


def _product(shape: Iterable[int]) -> int:
    result = 1
    for dimension in shape:
        result *= int(dimension)
    return result


def _short_case_id(case_id: str) -> str:
    prefix = "research_module_"
    if not case_id.startswith(prefix):
        raise ValueError("kernel ingress workload scope case id drift")
    return case_id.removeprefix(prefix)


def _assert_scope_contract(scope: object) -> None:
    if not isinstance(scope, Mapping):
        raise ValueError("kernel ingress workload scope scope must be object")
    _assert_exact_keys("scope", scope, _SCOPE_KEYS)
    if scope["dtype_policy_id"] != (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_DTYPE_POLICY_ID
    ):
        raise ValueError("kernel ingress workload scope dtype policy drift")
    if scope["correctness_reference_id"] != (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_CORRECTNESS_REFERENCE_ID
    ):
        raise ValueError("kernel ingress workload scope correctness reference drift")
    if scope["operation_family"] not in _OPERATION_FAMILY_ORDER:
        raise ValueError("kernel ingress workload scope operation family drift")
    if not isinstance(scope["problem_size_min"], int) or not isinstance(
        scope["problem_size_max"],
        int,
    ):
        raise ValueError("kernel ingress workload scope problem size drift")
    if scope["problem_size_min"] <= 0 or scope["problem_size_max"] <= 0:
        raise ValueError("kernel ingress workload scope problem size drift")
    if scope["problem_size_min"] > scope["problem_size_max"]:
        raise ValueError("kernel ingress workload scope problem size drift")
    for key in ("scope_id", "shape_profile_id"):
        value = scope[key]
        if not isinstance(value, str) or not value.startswith("kernel_ingress_"):
            raise ValueError(f"kernel ingress workload scope {key} drift")


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"kernel ingress workload scope {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError("kernel ingress workload scope report is not JSON") from exc
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress workload scope contains forbidden source or value material"
            )
    for key in ("source_evidence_digest", "workload_scope_digest"):
        value = report[key] if isinstance(report, Mapping) else None
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError("kernel ingress workload scope digest drift")


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
