"""Prove Kernel Ingress backend equivalence across bounded shape profiles."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

import numpy as np
from numpy.typing import NDArray

try:
    from examples.source_to_intent_research_kernel_ingress import (
        _MODULE_CASES,
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
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        _MODULE_CASES,
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

from tuc.backends import LinearAlgebraSimulatorBackend, VectorSimulatorBackend
from tuc.compiler import compile_graph
from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    ingest_triton_module_source_to_source_intent,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
)
from tuc.reference import (
    reference_elementwise,
    reference_matmul,
    reference_reduction_sum,
    reference_softmax,
)
from tuc.runtime import (
    RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    assert_runtime_backend_equivalence,
    build_runtime_backend_equivalence_report,
    build_runtime_reference_correctness_report,
    dump_runtime_backend_equivalence_report,
    dump_runtime_reference_correctness_report,
    execute_graph,
    runtime_backend_equivalence_report_to_dict,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_REPORT_SCHEMA_VERSION = (  # noqa: E501
    "tuc.source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT = (
    "source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.portability.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_ARTIFACT_POLICY = (
    "metadata_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_SOURCE_BOUNDARY = (
    "kernel_ingress_source_intent_shape_profiles_to_reference_cpu_and_trusted_simulators"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CLAIM = (
    "same_source_intent_preserves_public_outputs_across_backend_placements_and_shape_profiles"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_BASELINE_RUN_ID = (
    "reference_cpu"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CANDIDATE_RUN_ID = (
    "capability_selected_simulators"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"module_source":',
    "python_source",
    '"raw_source":',
    "raw_source_text",
    "raw_tensor_value",
    "secret.txt",
    "source_intent_payload",
    "tensor_value",
    "tl.dot",
    "tl.store",
)

FloatArray = NDArray[np.float64]
ShapeMap = dict[str, tuple[int, ...]]

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_policy",
        "baseline_backend_sequences",
        "blocked_execution_surfaces",
        "case_count",
        "cases",
        "candidate_backend_sequences",
        "comparison_count",
        "default_parser_status",
        "equivalence_claim",
        "equivalence_contract",
        "executor_contract",
        "frontend_ingress_contract",
        "kernel_ingress_backend_equivalence_contract",
        "kernel_ingress_backend_equivalence_digest",
        "kernel_ingress_backend_equivalence_shape_profiles_contract",
        "kernel_ingress_digest",
        "parser_status",
        "profile_count",
        "profile_ids",
        "raw_source_policy",
        "raw_value_policy",
        "schema_version",
        "source_boundary",
        "status",
        "trusted_executor_registry",
        "trusted_runtime_backends",
    }
)
_CASE_KEYS = frozenset(
    {
        "baseline_backend_sequence",
        "baseline_reference_correctness_digest",
        "baseline_run_id",
        "baseline_trace_step_count",
        "candidate_backend_sequence",
        "candidate_reference_correctness_digest",
        "candidate_run_id",
        "candidate_trace_step_count",
        "case_id",
        "comparison_count",
        "comparison_metadata_digest",
        "declared_tensor_shapes",
        "equivalence_report_digest",
        "graph_name",
        "kernel_name",
        "operation_families",
        "passed",
        "profile_case_id",
        "profile_id",
        "raw_value_policy",
        "run_count",
        "status",
        "terminal_outputs",
        "tensor_shape_digest",
    }
)
_DIGEST_KEYS = (
    "baseline_reference_correctness_digest",
    "candidate_reference_correctness_digest",
    "comparison_metadata_digest",
    "equivalence_report_digest",
    "tensor_shape_digest",
)
_PROFILE_IDS = ("base", "alternate")
_SHAPE_PROFILES: dict[str, dict[str, ShapeMap]] = {
    "base": {
        "research_matmul_elementwise": {"a": (4, 8), "b": (8, 2), "y": (4, 2)},
        "research_softmax_reduction": {"x": (4, 8), "y": (4,)},
        "research_softmax_elementwise": {"x": (4, 8), "y": (4, 8)},
        "research_matmul_reduction": {"a": (4, 8), "b": (8, 2), "y": (4,)},
        "research_mvp_pipeline": {"a": (4, 8), "b": (8, 4), "y": (4,)},
    },
    "alternate": {
        "research_matmul_elementwise": {"a": (3, 5), "b": (5, 4), "y": (3, 4)},
        "research_softmax_reduction": {"x": (3, 5), "y": (3,)},
        "research_softmax_elementwise": {"x": (3, 5), "y": (3, 5)},
        "research_matmul_reduction": {"a": (3, 5), "b": (5, 4), "y": (3,)},
        "research_mvp_pipeline": {"a": (3, 5), "b": (5, 3), "y": (3,)},
    },
}
_EXPECTED_CASES = {
    "research_module_matmul_elementwise": {
        "baseline_backend_sequence": ["reference-cpu", "reference-cpu"],
        "candidate_backend_sequence": ["linear-sim", "vector-sim"],
        "graph_name": "research_matmul_elementwise",
        "kernel_name": "matmul_elementwise",
        "operation_families": ["elementwise", "matmul"],
        "terminal_outputs": ["activated"],
        "trace_step_count": 2,
    },
    "research_module_softmax_reduction": {
        "baseline_backend_sequence": ["reference-cpu", "reference-cpu"],
        "candidate_backend_sequence": ["vector-sim", "vector-sim"],
        "graph_name": "research_softmax_reduction",
        "kernel_name": "softmax_reduction",
        "operation_families": ["reduction", "softmax"],
        "terminal_outputs": ["row_sum"],
        "trace_step_count": 2,
    },
    "research_module_matmul_reduction": {
        "baseline_backend_sequence": ["reference-cpu", "reference-cpu"],
        "candidate_backend_sequence": ["linear-sim", "vector-sim"],
        "graph_name": "research_matmul_reduction",
        "kernel_name": "matmul_reduction",
        "operation_families": ["matmul", "reduction"],
        "terminal_outputs": ["column_sum"],
        "trace_step_count": 2,
    },
    "research_module_softmax_elementwise": {
        "baseline_backend_sequence": ["reference-cpu", "reference-cpu"],
        "candidate_backend_sequence": ["vector-sim", "vector-sim"],
        "graph_name": "research_softmax_elementwise",
        "kernel_name": "softmax_elementwise",
        "operation_families": ["elementwise", "softmax"],
        "terminal_outputs": ["activated"],
        "trace_step_count": 2,
    },
    "research_module_mvp_pipeline": {
        "baseline_backend_sequence": [
            "reference-cpu",
            "reference-cpu",
            "reference-cpu",
            "reference-cpu",
        ],
        "candidate_backend_sequence": [
            "linear-sim",
            "vector-sim",
            "vector-sim",
            "vector-sim",
        ],
        "graph_name": "research_mvp_pipeline",
        "kernel_name": "mvp_pipeline",
        "operation_families": ["elementwise", "matmul", "reduction", "softmax"],
        "terminal_outputs": ["stable"],
        "trace_step_count": 4,
    },
}


def build_kernel_ingress_backend_equivalence_shape_profiles_report() -> dict[str, object]:
    """Return source-free backend equivalence evidence across shape profiles."""

    kernel_ingress_text = build_kernel_ingress_report()
    kernel_ingress = json.loads(kernel_ingress_text)
    assert_kernel_ingress_report_contract(kernel_ingress)
    backend_equivalence_text = build_kernel_ingress_backend_equivalence_report()
    backend_equivalence = json.loads(backend_equivalence_text)
    assert_kernel_ingress_backend_equivalence_report_contract(backend_equivalence)
    cases = [
        _build_case(case_id, source_name, kernel_name, module_source, profile_id)
        for case_id, source_name, kernel_name, module_source in _MODULE_CASES
        for profile_id in _PROFILE_IDS
    ]
    report: dict[str, object] = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_ARTIFACT_POLICY
        ),
        "baseline_backend_sequences": _unique_sequences(
            cases,
            "baseline_backend_sequence",
        ),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "case_count": len(cases),
        "cases": cases,
        "candidate_backend_sequences": _unique_sequences(
            cases,
            "candidate_backend_sequence",
        ),
        "comparison_count": sum(_int_value(case, "comparison_count") for case in cases),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "equivalence_claim": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CLAIM
        ),
        "equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "kernel_ingress_backend_equivalence_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT
        ),
        "kernel_ingress_backend_equivalence_digest": _digest(backend_equivalence_text),
        "kernel_ingress_backend_equivalence_shape_profiles_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT
        ),
        "kernel_ingress_digest": _digest(kernel_ingress_text),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "profile_count": len(_PROFILE_IDS),
        "profile_ids": list(_PROFILE_IDS),
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
        "trusted_runtime_backends": [
            "linear-sim",
            "reference-cpu",
            "vector-sim",
        ],
    }
    assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for Kernel Ingress shape-profile portability."""

    return json.dumps(
        build_kernel_ingress_backend_equivalence_shape_profiles_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_kernel_ingress_backend_equivalence_shape_profiles_report_contract(
    report: object,
) -> None:
    """Fail closed unless shape-profile backend equivalence matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError(
            "kernel ingress backend equivalence shape profiles report must be object"
        )
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    kernel_ingress_text = build_kernel_ingress_report()
    backend_equivalence_text = build_kernel_ingress_backend_equivalence_report()
    expected_values = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_ARTIFACT_POLICY
        ),
        "baseline_backend_sequences": [
            "reference-cpu->reference-cpu",
            "reference-cpu->reference-cpu->reference-cpu->reference-cpu",
        ],
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "case_count": len(_EXPECTED_CASES) * len(_PROFILE_IDS),
        "candidate_backend_sequences": [
            "linear-sim->vector-sim",
            "vector-sim->vector-sim",
            "linear-sim->vector-sim->vector-sim->vector-sim",
        ],
        "comparison_count": len(_EXPECTED_CASES) * len(_PROFILE_IDS),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "equivalence_claim": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CLAIM
        ),
        "equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "kernel_ingress_backend_equivalence_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT
        ),
        "kernel_ingress_backend_equivalence_digest": _digest(backend_equivalence_text),
        "kernel_ingress_backend_equivalence_shape_profiles_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT
        ),
        "kernel_ingress_digest": _digest(kernel_ingress_text),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "profile_count": len(_PROFILE_IDS),
        "profile_ids": list(_PROFILE_IDS),
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
        "trusted_runtime_backends": [
            "linear-sim",
            "reference-cpu",
            "vector-sim",
        ],
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(
                f"kernel ingress backend equivalence shape profiles {key} drift"
            )
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress backend equivalence shape profiles cases drift")
    observed_profile_case_ids = []
    for case in cases:
        observed_profile_case_ids.append(_assert_case_contract(case))
    expected_profile_case_ids = [
        f"{case_id}:{profile_id}"
        for case_id in _EXPECTED_CASES
        for profile_id in _PROFILE_IDS
    ]
    if observed_profile_case_ids != expected_profile_case_ids:
        raise ValueError(
            "kernel ingress backend equivalence shape profiles case order drift"
        )
    _assert_report_is_source_free(report)


def _build_case(
    case_id: str,
    source_name: str,
    kernel_name: str,
    module_source: str,
    profile_id: str,
) -> dict[str, object]:
    tensor_shapes = _tensor_shapes_for_profile(source_name, profile_id)
    ingress = ingest_triton_module_source_to_source_intent(
        module_source,
        source_name=source_name,
        kernel_name=kernel_name,
        tensor_shapes=tensor_shapes,
    )
    module = source_intent_from_mapping(ingress.parser_result.source_intent_payload)
    metadata = source_intent_to_triton_metadata(module)
    graph = metadata.to_compute_graph()
    baseline = compile_graph(graph, [])
    candidate = compile_graph(
        graph,
        [
            LinearAlgebraSimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    inputs = _inputs_for_profile(source_name, tensor_shapes)
    references = _references_for(source_name, inputs)
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    candidate_execution = execute_graph(
        candidate.hac_ir.graph,
        candidate.partition_plan,
        inputs,
    )
    baseline_correctness = build_runtime_reference_correctness_report(
        baseline.hac_ir.graph,
        baseline_execution,
        references,
    )
    candidate_correctness = build_runtime_reference_correctness_report(
        candidate.hac_ir.graph,
        candidate_execution,
        references,
    )
    if not baseline_correctness.passed or not candidate_correctness.passed:
        raise AssertionError(
            "kernel ingress backend equivalence shape profiles correctness failed"
        )
    equivalence = assert_runtime_backend_equivalence(
        build_runtime_backend_equivalence_report(
            graph,
            baseline.partition_plan,
            baseline_execution,
            candidate.partition_plan,
            candidate_execution,
            baseline_run_id=(
                SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_BASELINE_RUN_ID
            ),
            candidate_run_id=(
                SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CANDIDATE_RUN_ID
            ),
        )
    )
    equivalence_text = dump_runtime_backend_equivalence_report(equivalence)
    equivalence_report = runtime_backend_equivalence_report_to_dict(equivalence)
    return {
        "baseline_backend_sequence": _run_sequence(equivalence_report, 0),
        "baseline_reference_correctness_digest": _digest(
            dump_runtime_reference_correctness_report(baseline_correctness)
        ),
        "baseline_run_id": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_BASELINE_RUN_ID
        ),
        "baseline_trace_step_count": _run_step_count(equivalence_report, 0),
        "candidate_backend_sequence": _run_sequence(equivalence_report, 1),
        "candidate_reference_correctness_digest": _digest(
            dump_runtime_reference_correctness_report(candidate_correctness)
        ),
        "candidate_run_id": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CANDIDATE_RUN_ID
        ),
        "candidate_trace_step_count": _run_step_count(equivalence_report, 1),
        "case_id": case_id,
        "comparison_count": int(equivalence_report["comparison_count"]),
        "comparison_metadata_digest": str(
            equivalence_report["comparison_metadata_digest"]
        ),
        "declared_tensor_shapes": _shape_summary(tensor_shapes),
        "equivalence_report_digest": _digest(equivalence_text),
        "graph_name": str(equivalence_report["graph_name"]),
        "kernel_name": kernel_name,
        "operation_families": list(ingress.report.operation_families),
        "passed": bool(equivalence_report["passed"]),
        "profile_case_id": f"{case_id}:{profile_id}",
        "profile_id": profile_id,
        "raw_value_policy": str(equivalence_report["raw_value_policy"]),
        "run_count": int(equivalence_report["run_count"]),
        "status": "backend_equivalence_shape_profile_bound",
        "terminal_outputs": _comparison_outputs(equivalence_report),
        "tensor_shape_digest": _digest(_canonical_json(_shape_summary(tensor_shapes))),
    }


def _assert_case_contract(case: object) -> str:
    if not isinstance(case, Mapping):
        raise ValueError(
            "kernel ingress backend equivalence shape profiles case must be object"
        )
    _assert_exact_keys("case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASES:
        raise ValueError("kernel ingress backend equivalence shape profiles case id drift")
    profile_id = case["profile_id"]
    if not isinstance(profile_id, str) or profile_id not in _PROFILE_IDS:
        raise ValueError(
            "kernel ingress backend equivalence shape profiles profile id drift"
        )
    expected = _EXPECTED_CASES[case_id]
    for key in (
        "baseline_backend_sequence",
        "candidate_backend_sequence",
        "graph_name",
        "kernel_name",
        "operation_families",
        "terminal_outputs",
    ):
        if case[key] != expected[key]:
            raise ValueError(
                f"kernel ingress backend equivalence shape profiles {key} drift"
            )
    source_name = str(expected["graph_name"])
    expected_shapes = _shape_summary(_tensor_shapes_for_profile(source_name, profile_id))
    expected_values = {
        "baseline_run_id": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_BASELINE_RUN_ID
        ),
        "baseline_trace_step_count": expected["trace_step_count"],
        "candidate_run_id": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CANDIDATE_RUN_ID
        ),
        "candidate_trace_step_count": expected["trace_step_count"],
        "comparison_count": 1,
        "declared_tensor_shapes": expected_shapes,
        "passed": True,
        "profile_case_id": f"{case_id}:{profile_id}",
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "run_count": 2,
        "status": "backend_equivalence_shape_profile_bound",
        "tensor_shape_digest": _digest(_canonical_json(expected_shapes)),
    }
    for key, expected_value in expected_values.items():
        if case[key] != expected_value:
            raise ValueError(
                f"kernel ingress backend equivalence shape profiles {key} drift"
            )
    for key in _DIGEST_KEYS:
        value = case[key]
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError(
                "kernel ingress backend equivalence shape profiles digest drift"
            )
    return str(case["profile_case_id"])


def _tensor_shapes_for_profile(source_name: str, profile_id: str) -> ShapeMap:
    try:
        return dict(_SHAPE_PROFILES[profile_id][source_name])
    except KeyError as exc:
        raise ValueError(
            "unsupported kernel ingress backend equivalence shape profile"
        ) from exc


def _inputs_for_profile(
    source_name: str,
    tensor_shapes: Mapping[str, tuple[int, ...]],
) -> dict[str, FloatArray]:
    if source_name in (
        "research_matmul_elementwise",
        "research_matmul_reduction",
        "research_mvp_pipeline",
    ):
        return {
            "a": _finite_array(tensor_shapes["a"], offset=1.0),
            "b": _finite_array(tensor_shapes["b"], offset=-2.0),
        }
    if source_name == "research_softmax_elementwise":
        return {"x": _finite_array(tensor_shapes["x"], offset=0.5)}
    if source_name == "research_softmax_reduction":
        return {"x": _finite_array(tensor_shapes["x"], offset=0.5)}
    raise ValueError("unsupported kernel ingress backend equivalence source")


def _references_for(
    source_name: str,
    inputs: Mapping[str, FloatArray],
) -> dict[str, FloatArray]:
    if source_name == "research_matmul_elementwise":
        projection = reference_matmul(inputs["a"], inputs["b"])
        return {"activated": reference_elementwise(projection)}
    if source_name == "research_softmax_reduction":
        normalized = reference_softmax(inputs["x"], axis=1)
        return {"row_sum": reference_reduction_sum(normalized, axis=1)}
    if source_name == "research_softmax_elementwise":
        normalized = reference_softmax(inputs["x"], axis=1)
        return {"activated": reference_elementwise(normalized)}
    if source_name == "research_matmul_reduction":
        projection = reference_matmul(inputs["a"], inputs["b"])
        return {"column_sum": reference_reduction_sum(projection, axis=1)}
    if source_name == "research_mvp_pipeline":
        projection = reference_matmul(inputs["a"], inputs["b"])
        normalized = reference_softmax(projection, axis=1)
        row_sum = reference_reduction_sum(normalized, axis=1)
        return {"stable": reference_elementwise(row_sum)}
    raise ValueError("unsupported kernel ingress backend equivalence source")


def _finite_array(shape: tuple[int, ...], *, offset: float) -> FloatArray:
    value_count = int(np.prod(shape))
    values = np.arange(value_count, dtype=np.float64).reshape(shape)
    return ((values % 19.0) - 9.0 + offset) / 7.0


def _shape_summary(shapes: Mapping[str, tuple[int, ...]]) -> dict[str, list[int]]:
    return {name: [int(dimension) for dimension in shape] for name, shape in shapes.items()}


def _run_sequence(report: Mapping[str, object], index: int) -> list[str]:
    runs = report["runs"]
    if not isinstance(runs, list) or not isinstance(runs[index], Mapping):
        raise ValueError("kernel ingress backend equivalence shape profiles run drift")
    sequence = runs[index]["planned_backend_sequence"]
    if not isinstance(sequence, list):
        raise ValueError(
            "kernel ingress backend equivalence shape profiles run sequence drift"
        )
    return [str(item) for item in sequence]


def _run_step_count(report: Mapping[str, object], index: int) -> int:
    runs = report["runs"]
    if not isinstance(runs, list) or not isinstance(runs[index], Mapping):
        raise ValueError("kernel ingress backend equivalence shape profiles run drift")
    return int(runs[index]["trace_step_count"])


def _comparison_outputs(report: Mapping[str, object]) -> list[str]:
    comparisons = report["comparisons"]
    if not isinstance(comparisons, list):
        raise ValueError(
            "kernel ingress backend equivalence shape profiles comparison drift"
        )
    outputs: list[str] = []
    for comparison in comparisons:
        if not isinstance(comparison, Mapping):
            raise ValueError(
                "kernel ingress backend equivalence shape profiles comparison drift"
            )
        if comparison["comparison_status"] != "matched":
            raise ValueError(
                "kernel ingress backend equivalence shape profiles comparison failed"
            )
        outputs.append(str(comparison["tensor_name"]))
    return outputs


def _unique_sequences(cases: list[dict[str, object]], key: str) -> list[str]:
    observed: list[str] = []
    for case in cases:
        sequence = case[key]
        if not isinstance(sequence, list):
            raise ValueError(
                "kernel ingress backend equivalence shape profiles sequence drift"
            )
        rendered = "->".join(str(item) for item in sequence)
        if rendered not in observed:
            observed.append(rendered)
    return observed


def _int_value(payload: Mapping[str, object], key: str) -> int:
    value = payload[key]
    if not isinstance(value, int):
        raise ValueError(
            "kernel ingress backend equivalence shape profiles count drift"
        )
    return value


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(
            f"kernel ingress backend equivalence shape profiles {context} drift"
        )


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = _canonical_json(report)
    except TypeError as exc:
        raise ValueError(
            "kernel ingress backend equivalence shape profiles report is not JSON"
        ) from exc
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress backend equivalence shape profiles contains "
                "forbidden source or value material"
            )


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
